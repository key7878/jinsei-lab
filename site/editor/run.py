"""
人生ラボ編集長AI CLI。

使い方:
  python run.py context             # context.jsonを組み立てて site/editor/context.json に書き出す
  python run.py theme               # 今日のテーマを選定し、drafts/{date}/theme_decision.json に書き出す
  python run.py content [theme_id]  # Threads3本+noteドラフトを生成し、drafts/{date}/content_draft.json に書き出す
                                     # theme_id省略時は本日日付のtheme_decision.jsonを使う
  python run.py brief [date]        # Daily Briefを組み立て、drafts/{date}/brief.md に書き出す
                                     # date省略時は本日日付を使う

サブコマンドを追加していく前提のCLI構造(argparse)。
将来的に `python run.py brief` 等を追加する場合は、
build_parser() にサブパーサーを1つ足し、対応する cmd_* 関数を実装するだけでよい。
"""

import argparse
import json
import sys

from context_assembly import write_context


def cmd_context(args):
    path = write_context()
    print(f"wrote {path}")


def cmd_theme(args):
    from generators.select_theme import select_theme, ThemeSelectionError

    try:
        decision = select_theme()
    except ThemeSelectionError as e:
        print(f"ERROR: {e}")
        print("--- raw LLM output ---")
        print(e.raw_output)
        sys.exit(1)

    print(json.dumps(decision, ensure_ascii=False, indent=2))


def cmd_content(args):
    from generators.generate_content import generate_content, ContentGenerationError

    try:
        content = generate_content(args.theme_id)
    except ContentGenerationError as e:
        print(f"ERROR: {e}")
        print("--- raw LLM output ---")
        print(e.raw_output)
        sys.exit(1)

    print(json.dumps(content, ensure_ascii=False, indent=2))


def cmd_brief(args):
    import os
    from datetime import datetime
    from brief import build_brief
    from _paths import load_config, resolve_path

    try:
        brief_md = build_brief(args.date)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    date = args.date or datetime.now().strftime("%Y-%m-%d")
    config = load_config()
    date_dir = os.path.join(resolve_path(config["paths"]["drafts_dir"]), date)
    out_path = os.path.join(date_dir, "brief.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(brief_md)
    print(f"wrote {out_path}")

    print(brief_md)


def build_parser():
    parser = argparse.ArgumentParser(prog="run.py", description="人生ラボ編集長AI CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    context_parser = subparsers.add_parser("context", help="context.jsonを組み立てて書き出す")
    context_parser.set_defaults(func=cmd_context)

    theme_parser = subparsers.add_parser("theme", help="今日の発信テーマを選定する")
    theme_parser.set_defaults(func=cmd_theme)

    content_parser = subparsers.add_parser(
        "content", help="Threads3本+noteドラフトを生成する"
    )
    content_parser.add_argument(
        "theme_id", nargs="?", default=None,
        help="対象のtheme_id(省略時は本日日付のtheme_decision.jsonを使う)",
    )
    content_parser.set_defaults(func=cmd_content)

    brief_parser = subparsers.add_parser("brief", help="Daily Briefを組み立てる")
    brief_parser.add_argument(
        "date", nargs="?", default=None,
        help="対象の日付(YYYY-MM-DD、省略時は本日日付)",
    )
    brief_parser.set_defaults(func=cmd_brief)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
