"""
site/editor/prompts/theme_select.md を組み立てて実行し、
今日の発信テーマ選定結果を site/editor/drafts/{date}/theme_decision.json として書き出す。
"""

import os
import sys
import json

_HERE = os.path.dirname(os.path.abspath(__file__))         # site/editor/generators/
_EDITOR_DIR = os.path.dirname(_HERE)                         # site/editor/
sys.path.insert(0, _EDITOR_DIR)
sys.path.insert(0, _HERE)

from _paths import load_config, resolve_path  # noqa: E402
from _client import call_llm, strip_code_fence  # noqa: E402

PROMPT_PATH = os.path.join(_EDITOR_DIR, "prompts", "theme_select.md")
CONTEXT_PATH = os.path.join(_EDITOR_DIR, "context.json")

LABS = ["career", "ai", "childcare", "english", "money"]

REQUIRED_FIELDS = [
    "theme_id", "date", "lab", "title_draft", "reasoning", "target_reader",
    "funnel_goal", "cta_type", "cta_placement_note", "related_article_ids",
    "utm_campaign", "alternates",
]
ALLOWED_FIELDS = set(REQUIRED_FIELDS)


class ThemeSelectionError(Exception):
    """LLM出力の検証に失敗した場合に送出する。raw_outputに生の出力を保持する。"""

    def __init__(self, message, raw_output=None):
        super().__init__(message)
        self.raw_output = raw_output


def _build_prompt(config) -> str:
    if not os.path.exists(CONTEXT_PATH):
        raise FileNotFoundError(
            f"{CONTEXT_PATH} が見つかりません。先に `python run.py context` を実行してください。"
        )
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        template = f.read()
    with open(CONTEXT_PATH, "r", encoding="utf-8") as f:
        context_json_str = f.read()

    # GUIDELINES.md/HARU.mdはLLM側にツール呼び出しで読ませず、
    # ここでPython側が読み込んでプロンプトに直接埋め込む。
    # (claude -pにはTTYが無く、ツール使用の許可プロンプトで止まってしまうため)
    guidelines_path = resolve_path(config["paths"]["guidelines_path"])
    haru_persona_path = resolve_path(config["paths"]["haru_persona_path"])
    with open(guidelines_path, "r", encoding="utf-8") as f:
        guidelines_content = f.read()
    with open(haru_persona_path, "r", encoding="utf-8") as f:
        haru_persona_content = f.read()

    # .format()ではなく単純な文字列置換にする。埋め込む内容(特にcontext_json_str)が
    # {...}を大量に含むため、.format()だとその中括弧と衝突する。
    prompt = template.replace("{context_json}", context_json_str)
    prompt = prompt.replace("{guidelines_content}", guidelines_content)
    prompt = prompt.replace("{haru_persona_content}", haru_persona_content)
    return prompt


def _load_existing_article_ids():
    with open(CONTEXT_PATH, "r", encoding="utf-8") as f:
        context = json.load(f)
    return {a["id"] for a in context.get("existing_articles", [])}


def _validate(decision, config, raw_output, existing_article_ids):
    if not isinstance(decision, dict):
        raise ThemeSelectionError(
            f"LLM出力のトップレベルがオブジェクトではありません: {type(decision).__name__}",
            raw_output,
        )

    missing = [f for f in REQUIRED_FIELDS if f not in decision]
    if missing:
        raise ThemeSelectionError(f"必須フィールドが不足しています: {missing}", raw_output)

    extra_keys = set(decision.keys()) - ALLOWED_FIELDS
    if extra_keys:
        raise ThemeSelectionError(
            f"スキーマに無い余分なキーが含まれています: {sorted(extra_keys)}", raw_output
        )

    if decision["lab"] not in LABS:
        raise ThemeSelectionError(
            f"lab が不正です: {decision['lab']!r} (期待値: {LABS})", raw_output
        )

    if decision["funnel_goal"] not in config["funnel_goals"]:
        raise ThemeSelectionError(
            f"funnel_goal が不正です: {decision['funnel_goal']!r} "
            f"(期待値: {config['funnel_goals']})",
            raw_output,
        )

    if decision["cta_type"] not in config["cta_types"]:
        raise ThemeSelectionError(
            f"cta_type が不正です: {decision['cta_type']!r} (期待値: {config['cta_types']})",
            raw_output,
        )

    expected_prefix = f"theme-{str(decision['date']).replace('-', '')}-"
    if not str(decision["theme_id"]).startswith(expected_prefix):
        raise ThemeSelectionError(
            f"theme_id が date と整合していません: theme_id={decision['theme_id']!r}, "
            f"date={decision['date']!r} (期待するprefix: {expected_prefix!r})",
            raw_output,
        )

    alternates = decision.get("alternates")
    if not isinstance(alternates, list) or len(alternates) != 2:
        raise ThemeSelectionError(
            f"alternates は2件の配列である必要があります: {alternates!r}", raw_output
        )
    for alt in alternates:
        if not isinstance(alt, dict) or "lab" not in alt:
            raise ThemeSelectionError(f"alternates の要素が不正です: {alt!r}", raw_output)
        if alt["lab"] == decision["lab"]:
            raise ThemeSelectionError(
                f"alternates の lab が primary({decision['lab']!r}) と同じです: {alt!r}",
                raw_output,
            )

    related_ids = decision.get("related_article_ids") or []
    unknown_ids = [rid for rid in related_ids if rid not in existing_article_ids]
    if unknown_ids:
        raise ThemeSelectionError(
            f"related_article_ids に existing_articles に存在しないIDが含まれています: "
            f"{unknown_ids}",
            raw_output,
        )


def select_theme() -> dict:
    """theme_select.mdを実行し、検証済みのtheme decisionをdraftsに書き出して返す。

    検証に失敗した場合はThemeSelectionErrorを送出する(黙って補正しない)。
    e.raw_output に生のLLM出力が入っている。
    """
    config = load_config()
    prompt = _build_prompt(config)

    raw_output = call_llm(prompt)
    cleaned = strip_code_fence(raw_output)

    try:
        decision = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ThemeSelectionError(f"LLM出力が有効なJSONではありません: {e}", raw_output)

    existing_article_ids = _load_existing_article_ids()
    _validate(decision, config, raw_output, existing_article_ids)

    drafts_dir = resolve_path(config["paths"]["drafts_dir"])
    date_dir = os.path.join(drafts_dir, decision["date"])
    os.makedirs(date_dir, exist_ok=True)
    out_path = os.path.join(date_dir, "theme_decision.json")

    if os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                old_theme_id = json.load(f).get("theme_id", "?")
        except (OSError, json.JSONDecodeError):
            old_theme_id = "?"
        print(
            f"WARN: {out_path} は既に存在します(theme_id={old_theme_id!r})。"
            f"theme_id={decision['theme_id']!r} で上書きします。"
        )

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(decision, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"wrote {out_path}")
    return decision


if __name__ == "__main__":
    try:
        result = select_theme()
    except ThemeSelectionError as e:
        print(f"ERROR: {e}")
        print("--- raw LLM output ---")
        print(e.raw_output)
        sys.exit(1)
    print(json.dumps(result, ensure_ascii=False, indent=2))
