"""
site/editor/drafts/{date}/theme_decision.json と content_draft.json から、
毎朝5〜10分で確認できるDaily Brief(Markdown)を組み立てる。

LLM呼び出しは一切なし。純粋な文字列整形のみ。
"""

import os
import sys
import json
from datetime import datetime

_EDITOR_DIR = os.path.dirname(os.path.abspath(__file__))  # site/editor/
sys.path.insert(0, _EDITOR_DIR)
from _paths import load_config, resolve_path  # noqa: E402

# Threadsの表示順は content_draft.json 内の配列順に依存せず、この固定順を使う。
THREAD_ROLE_ORDER = ["専門知識", "共感・等身大", "note誘導"]

TEMPLATE = """# {date} Daily Brief

## 今日のテーマ
- **{title_draft}**（{lab}）
- なぜ今日: {reasoning}
- 想定読者: {target_reader}
- ファネル: {funnel_goal}

## 次点（不採用時の控え）
- {alt0_title}（{alt0_lab}）
- {alt1_title}（{alt1_lab}）

## Threads（3本）

{threads_section}

確認ポイント：「多くの場合」「実際に」など、集計的な実績を匂わせる語調が無いか

## CTA方針
- 種別: {cta_type}
- 配置: {cta_placement_note}

## noteドラフト（全文は週次レビューへ）
- タイトル: {note_title}
- リード: {note_lead}
- 全文: content_draft.json を参照
"""


def _date_dir(date, config):
    drafts_dir = resolve_path(config["paths"]["drafts_dir"])
    return os.path.join(drafts_dir, date)


def _load_json_or_die(path, hint):
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} が見つかりません。{hint}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _thread_text_by_role(threads, role):
    for t in threads:
        if t.get("role") == role:
            return t.get("text", "")
    raise ValueError(f"threads に role={role!r} が見つかりません: {threads!r}")


def _render_thread_blockquote(text, indent="  "):
    """textを段落構造(\\n)を保ったまま、インデント付きの引用(>)に変換する。

    空行は"> "ではなく">"のみ(末尾スペースなし)にする。
    """
    lines = []
    for line in text.split("\n"):
        lines.append(f"{indent}>" if line == "" else f"{indent}> {line}")
    return "\n".join(lines)


def _render_threads_section(thread_texts):
    """チェックボックス行(role名のみの単独行)+その下にぶら下がる引用ブロックを組み立てる。

    チェックボックス行を役割名のみの単独行にしているのは、将来 `run.py approve` が
    この行を正規表現でパースする前提のため(本文と混在させない)。
    """
    blocks = []
    for role in THREAD_ROLE_ORDER:
        blockquote = _render_thread_blockquote(thread_texts[role])
        blocks.append(f"- [ ] **{role}**\n{blockquote}")
    return "\n\n".join(blocks)


def build_brief(date: str = None) -> str:
    """theme_decision.json / content_draft.json からDaily Brief(Markdown文字列)を組み立てる。

    date省略時は本日日付を使う。
    theme_decision.json / content_draft.json のいずれかが無い場合は
    FileNotFoundErrorを送出する(黙って空欄で埋めない)。
    """
    config = load_config()
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    date_dir = _date_dir(date, config)
    theme_path = os.path.join(date_dir, "theme_decision.json")
    content_path = os.path.join(date_dir, "content_draft.json")

    theme = _load_json_or_die(theme_path, "先に `python run.py theme` を実行してください。")
    content = _load_json_or_die(content_path, "先に `python run.py content` を実行してください。")

    alternates = theme.get("alternates") or []
    if len(alternates) < 2:
        raise ValueError(f"{theme_path} の alternates が2件ありません: {alternates!r}")

    threads = content.get("threads") or []
    thread_texts = {role: _thread_text_by_role(threads, role) for role in THREAD_ROLE_ORDER}
    threads_section = _render_threads_section(thread_texts)

    note_draft = content.get("note_draft") or {}

    return TEMPLATE.format(
        date=date,
        title_draft=theme["title_draft"],
        lab=theme["lab"],
        reasoning=theme["reasoning"],
        target_reader=theme["target_reader"],
        funnel_goal=theme["funnel_goal"],
        alt0_title=alternates[0]["title_draft"],
        alt0_lab=alternates[0]["lab"],
        alt1_title=alternates[1]["title_draft"],
        alt1_lab=alternates[1]["lab"],
        threads_section=threads_section,
        cta_type=theme["cta_type"],
        cta_placement_note=theme["cta_placement_note"],
        note_title=note_draft.get("title", ""),
        note_lead=note_draft.get("lead", ""),
    )


if __name__ == "__main__":
    arg_date = sys.argv[1] if len(sys.argv) > 1 else None
    print(build_brief(arg_date))
