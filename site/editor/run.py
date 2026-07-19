"""
人生ラボ編集長AI CLI。

使い方:
  python run.py context   # context.jsonを組み立てて site/editor/context.json に書き出す
  python run.py theme     # 今日のテーマを選定し、drafts/{date}/theme_decision.json に書き出す

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


def build_parser():
    parser = argparse.ArgumentParser(prog="run.py", description="人生ラボ編集長AI CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    context_parser = subparsers.add_parser("context", help="context.jsonを組み立てて書き出す")
    context_parser.set_defaults(func=cmd_context)

    theme_parser = subparsers.add_parser("theme", help="今日の発信テーマを選定する")
    theme_parser.set_defaults(func=cmd_theme)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
