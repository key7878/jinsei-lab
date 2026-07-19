"""
site/editor/prompts/generate_content.md を組み立てて実行し、
本日確定したテーマからThreads投稿3本とnoteドラフト1本を生成する。

site/editor/drafts/{date}/content_draft.json として書き出す。
"""

import os
import sys
import json
import re

_HERE = os.path.dirname(os.path.abspath(__file__))         # site/editor/generators/
_EDITOR_DIR = os.path.dirname(_HERE)                         # site/editor/
sys.path.insert(0, _EDITOR_DIR)
sys.path.insert(0, _HERE)

from _paths import load_config, resolve_path  # noqa: E402
from _client import call_llm, strip_code_fence  # noqa: E402

PROMPT_PATH = os.path.join(_EDITOR_DIR, "prompts", "generate_content.md")
CONTEXT_PATH = os.path.join(_EDITOR_DIR, "context.json")

TOP_LEVEL_ALLOWED = {"theme_id", "threads", "note_draft"}
THREAD_ROLES = ["専門知識", "共感・等身大", "note誘導"]
THREAD_ALLOWED_KEYS = {"role", "text"}
NOTE_DRAFT_ALLOWED = {
    "title", "lead", "body_markdown", "headings", "summary", "cta",
    "hashtags", "eyecatch_image_prompt",
}

_THEME_ID_DATE_RE = re.compile(r"^theme-(\d{4})(\d{2})(\d{2})-")


class ContentGenerationError(Exception):
    """LLM出力の検証に失敗した場合に送出する。raw_outputに生の出力を保持する。"""

    def __init__(self, message, raw_output=None):
        super().__init__(message)
        self.raw_output = raw_output


def _resolve_theme_decision_path(theme_id, config):
    """theme_idから対象のtheme_decision.jsonのパスを解決する。

    theme_idを省略した場合: 本日日付の drafts/{today}/theme_decision.json を読む
    (drafts配下は日付ごとに1ファイルのみ保持する運用のため、単純にその日のファイルを読む)。

    theme_idを指定した場合: theme_idの日付部分からdraftsディレクトリを特定し、
    ファイル内のtheme_idが一致するか確認する(同日に複数回 `run.py theme` が実行され
    上書きされていた場合、要求されたtheme_idが既に失われている可能性があるため)。
    """
    import datetime

    drafts_dir = resolve_path(config["paths"]["drafts_dir"])

    if theme_id is None:
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        path = os.path.join(drafts_dir, date_str, "theme_decision.json")
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"{path} が見つかりません。先に `python run.py theme` を実行してください。"
            )
        return path

    m = _THEME_ID_DATE_RE.match(theme_id)
    if not m:
        raise ValueError(
            f"theme_id の形式が不正です: {theme_id!r} (期待形式: theme-YYYYMMDD-x)"
        )
    date_str = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    path = os.path.join(drafts_dir, date_str, "theme_decision.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} が見つかりません(theme_id={theme_id!r})。")

    with open(path, "r", encoding="utf-8") as f:
        on_disk_theme_id = json.load(f).get("theme_id")
    if on_disk_theme_id != theme_id:
        raise ValueError(
            f"要求された theme_id={theme_id!r} は {path} に存在しません。"
            f"現在保存されているのは theme_id={on_disk_theme_id!r} で、"
            f"同日の再実行により上書きされた可能性があります。"
        )
    return path


def _resolve_related_articles(related_article_ids):
    """related_article_idsをexisting_articlesから解決し、{id, title, url}の配列にする。

    select_theme側の検証を通過している前提だが、念のための二重チェックとして、
    見つからないIDが1つでもあればエラーにする。
    """
    with open(CONTEXT_PATH, "r", encoding="utf-8") as f:
        context = json.load(f)
    by_id = {a["id"]: a for a in context.get("existing_articles", [])}

    resolved = []
    missing = []
    for rid in related_article_ids:
        article = by_id.get(rid)
        if article is None:
            missing.append(rid)
            continue
        resolved.append({"id": article["id"], "title": article["title"], "url": article["url"]})

    if missing:
        raise ValueError(
            f"theme_decision.related_article_ids に existing_articles で見つからないIDが"
            f"あります: {missing} (select_theme側の検証を通過しているはずですが、"
            f"念のための二重チェックで検出しました)"
        )
    return resolved


def _build_prompt(config, theme_decision, related_articles_resolved) -> str:
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    # GUIDELINES.md/HARU.mdはLLM側にツール呼び出しで読ませず、
    # ここでPython側が読み込んでプロンプトに直接埋め込む(select_theme.pyと同じ方式)。
    guidelines_path = resolve_path(config["paths"]["guidelines_path"])
    haru_persona_path = resolve_path(config["paths"]["haru_persona_path"])
    with open(guidelines_path, "r", encoding="utf-8") as f:
        guidelines_content = f.read()
    with open(haru_persona_path, "r", encoding="utf-8") as f:
        haru_persona_content = f.read()

    theme_decision_json_str = json.dumps(theme_decision, ensure_ascii=False, indent=2)
    related_articles_str = json.dumps(related_articles_resolved, ensure_ascii=False, indent=2)

    # .format()ではなく単純な文字列置換にする。埋め込む内容が{...}を大量に含むため。
    prompt = template.replace("{guidelines_content}", guidelines_content)
    prompt = prompt.replace("{haru_persona_content}", haru_persona_content)
    prompt = prompt.replace("{theme_decision_json}", theme_decision_json_str)
    prompt = prompt.replace("{related_articles_resolved}", related_articles_str)
    return prompt


def _validate_content(content, theme_decision, prohibited_words, raw_output):
    if not isinstance(content, dict):
        raise ContentGenerationError(
            f"LLM出力のトップレベルがオブジェクトではありません: {type(content).__name__}",
            raw_output,
        )

    actual_keys = set(content.keys())
    if actual_keys != TOP_LEVEL_ALLOWED:
        raise ContentGenerationError(
            f"トップレベルのキー集合が一致しません。"
            f"余分: {sorted(actual_keys - TOP_LEVEL_ALLOWED)}, "
            f"不足: {sorted(TOP_LEVEL_ALLOWED - actual_keys)}",
            raw_output,
        )

    if content["theme_id"] != theme_decision["theme_id"]:
        raise ContentGenerationError(
            f"theme_id が入力と一致しません: 出力={content['theme_id']!r}, "
            f"入力={theme_decision['theme_id']!r}",
            raw_output,
        )

    threads = content["threads"]
    if not isinstance(threads, list) or len(threads) != 3:
        raise ContentGenerationError(
            f"threads は3件の配列である必要があります: {threads!r}", raw_output
        )
    for t in threads:
        if not isinstance(t, dict) or set(t.keys()) != THREAD_ALLOWED_KEYS:
            raise ContentGenerationError(f"threads の要素のキーが不正です: {t!r}", raw_output)

    roles = sorted(t["role"] for t in threads)
    if roles != sorted(THREAD_ROLES):
        raise ContentGenerationError(
            f"threads の role が不正です: {[t['role'] for t in threads]!r} "
            f"(期待値: {THREAD_ROLES} を重複なく1回ずつ)",
            raw_output,
        )

    note_draft = content["note_draft"]
    if not isinstance(note_draft, dict):
        raise ContentGenerationError(
            f"note_draft がオブジェクトではありません: {type(note_draft).__name__}", raw_output
        )
    note_keys = set(note_draft.keys())
    if note_keys != NOTE_DRAFT_ALLOWED:
        raise ContentGenerationError(
            f"note_draft のキー集合が一致しません。"
            f"余分: {sorted(note_keys - NOTE_DRAFT_ALLOWED)}, "
            f"不足: {sorted(NOTE_DRAFT_ALLOWED - note_keys)}",
            raw_output,
        )

    # prohibited_hype_words: threadsの各text、note_draftのtitle・body_markdownを
    # 部分文字列一致でチェックする。
    texts_to_check = [t["text"] for t in threads]
    texts_to_check.append(str(note_draft.get("title", "")))
    texts_to_check.append(str(note_draft.get("body_markdown", "")))

    found_words = sorted({
        word for word in prohibited_words
        if any(word in text for text in texts_to_check)
    })
    if found_words:
        raise ContentGenerationError(
            f"prohibited_hype_words に該当する語が含まれています: {found_words}", raw_output
        )


def generate_content(theme_id: str = None) -> dict:
    """theme_decision.jsonからThreads3本+noteドラフトを生成し、検証してdraftsに書き出す。

    検証に失敗した場合はContentGenerationErrorを送出する(黙って補正しない)。
    e.raw_output に生のLLM出力が入っている。
    """
    config = load_config()

    theme_decision_path = _resolve_theme_decision_path(theme_id, config)
    with open(theme_decision_path, "r", encoding="utf-8") as f:
        theme_decision = json.load(f)

    related_articles_resolved = _resolve_related_articles(
        theme_decision.get("related_article_ids") or []
    )

    prompt = _build_prompt(config, theme_decision, related_articles_resolved)
    raw_output = call_llm(prompt)
    cleaned = strip_code_fence(raw_output)

    try:
        content = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ContentGenerationError(f"LLM出力が有効なJSONではありません: {e}", raw_output)

    _validate_content(content, theme_decision, config["prohibited_hype_words"], raw_output)

    drafts_dir = resolve_path(config["paths"]["drafts_dir"])
    date_dir = os.path.join(drafts_dir, theme_decision["date"])
    os.makedirs(date_dir, exist_ok=True)
    out_path = os.path.join(date_dir, "content_draft.json")

    if os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                old_theme_id = json.load(f).get("theme_id", "?")
        except (OSError, json.JSONDecodeError):
            old_theme_id = "?"
        print(
            f"WARN: {out_path} は既に存在します(theme_id={old_theme_id!r})。"
            f"theme_id={content['theme_id']!r} で上書きします。"
        )

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"wrote {out_path}")
    return content


if __name__ == "__main__":
    arg_theme_id = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        result = generate_content(arg_theme_id)
    except ContentGenerationError as e:
        print(f"ERROR: {e}")
        print("--- raw LLM output ---")
        print(e.raw_output)
        sys.exit(1)
    print(json.dumps(result, ensure_ascii=False, indent=2))
