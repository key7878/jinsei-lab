"""
site/editor/drafts/{date}/brief.md のチェック済み(- [x])Threads項目を、
sns_queue_approved.csv に追記する承認フロー。

LLM呼び出しなし。既存の sns_queue.csv には一切触れない(build.pyが記事公開のたびに
まるごと書き直すファイルのため、そこに直接追記すると次のbuild.py実行で消える)。
承認済み投稿は完全に別ファイル(sns_queue_approved.csv、sns_queue.csvと同じ
ディレクトリ=site/直下)に追記する。

安全のため、書き込みは常に対話的な確認(input())を挟んでから行う。
"""

import os
import re
import sys
import csv

_EDITOR_DIR = os.path.dirname(os.path.abspath(__file__))  # site/editor/
sys.path.insert(0, _EDITOR_DIR)
from _paths import load_config, resolve_path  # noqa: E402

# sns_queue.csvと同じ基準(site/)からの相対パスで解決する。
# config.yamlにsns_queue*.csv専用のpaths項目は無いため、固定のファイル名を使う。
APPROVED_CSV_FILENAME = "sns_queue_approved.csv"

ROLE_CODE = {
    "専門知識": "expert",
    "共感・等身大": "empathy",
    "note誘導": "note-cta",
}

_CHECKBOX_RE = re.compile(r"^- \[([ xX])\] \*\*(.+?)\*\*(.*)$")
_ALREADY_PROCESSED_SUBSTRING = f"{APPROVED_CSV_FILENAME}に追加済み"
_PROCESSED_MARKER = f" → {APPROVED_CSV_FILENAME}に追加済み"


class ApproveError(Exception):
    """承認処理でファイルが見つからない・形式が不正な場合に送出する。"""


def _approved_csv_path():
    return resolve_path(APPROVED_CSV_FILENAME)


def _date_dir(date, config):
    drafts_dir = resolve_path(config["paths"]["drafts_dir"])
    return os.path.join(drafts_dir, date)


def _dequote_line(line):
    """"  >" または "  > content" から元の行(空行 or content)を復元する。"""
    rest = line[3:]  # "  >" の3文字を除去
    return rest[1:] if rest.startswith(" ") else rest


def _parse_threads_section(brief_text):
    """brief.mdの全文から、Threadsチェックボックス項目を抽出する。

    Returns:
        (items, lines): itemsは各要素が
            {role, checked, already_processed, text, line_index} の辞書。
            linesはbrief_text.split("\\n")の結果(後でマーカー書き込みに使う)。
    """
    lines = brief_text.split("\n")
    items = []
    current = None

    def flush():
        nonlocal current
        if current is not None:
            items.append({
                "role": current["role"],
                "checked": current["checked"],
                "already_processed": _ALREADY_PROCESSED_SUBSTRING in current["trailing"],
                "text": "\n".join(current["body_lines"]),
                "line_index": current["line_index"],
            })
        current = None

    for i, line in enumerate(lines):
        m = _CHECKBOX_RE.match(line)
        if m:
            flush()
            current = {
                "role": m.group(2),
                "checked": m.group(1).lower() == "x",
                "trailing": m.group(3).strip(),
                "body_lines": [],
                "line_index": i,
            }
            continue
        if current is not None:
            if line.startswith("  >"):
                current["body_lines"].append(_dequote_line(line))
            else:
                flush()
    flush()

    return items, lines


def _flatten_text(text):
    """sns_queue.csv本体と同じ変換: 段落改行を " / " に平坦化する(build.pyのflat_textと同じ規則)。"""
    return text.strip().replace("\n", " / ")


def _load_theme_decision(date_dir):
    path = os.path.join(date_dir, "theme_decision.json")
    if not os.path.exists(path):
        raise ApproveError(f"{path} が見つかりません。先に `python run.py theme` を実行してください。")
    import json
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def prepare_approval(date: str = None):
    """brief.mdを読み、承認対象(チェック済み・未処理)の項目とCSV行を組み立てる。

    実際の書き込みは行わない(プレビュー専用)。

    Returns:
        dict: {
            "date": str, "date_dir": str, "brief_path": str, "brief_lines": list[str],
            "csv_path": str,
            "to_append": list[dict]  # 各要素 {role, line_index, slug, lab, text_flat}
            "skipped_unchecked": int, "skipped_already_processed": int,
        }
    """
    config = load_config()
    if date is None:
        from datetime import datetime
        date = datetime.now().strftime("%Y-%m-%d")

    date_dir = _date_dir(date, config)
    brief_path = os.path.join(date_dir, "brief.md")
    if not os.path.exists(brief_path):
        raise ApproveError(f"{brief_path} が見つかりません。先に `python run.py brief` を実行してください。")

    with open(brief_path, "r", encoding="utf-8") as f:
        brief_text = f.read()

    items, brief_lines = _parse_threads_section(brief_text)

    theme_decision = _load_theme_decision(date_dir)
    theme_id = theme_decision["theme_id"]
    lab = theme_decision["lab"]

    to_append = []
    skipped_unchecked = 0
    skipped_already_processed = 0

    for item in items:
        if item["already_processed"]:
            skipped_already_processed += 1
            continue
        if not item["checked"]:
            skipped_unchecked += 1
            continue

        role = item["role"]
        role_code = ROLE_CODE.get(role)
        if role_code is None:
            raise ApproveError(
                f"{brief_path} に未知のrole={role!r} があります(既知: {list(ROLE_CODE)})"
            )

        to_append.append({
            "role": role,
            "line_index": item["line_index"],
            "slug": f"{theme_id}-{role_code}",
            "lab": lab,
            "text_flat": _flatten_text(item["text"]),
        })

    return {
        "date": date,
        "date_dir": date_dir,
        "brief_path": brief_path,
        "brief_lines": brief_lines,
        "csv_path": _approved_csv_path(),
        "to_append": to_append,
        "skipped_unchecked": skipped_unchecked,
        "skipped_already_processed": skipped_already_processed,
    }


def commit_approval(plan: dict):
    """prepare_approval()の結果を実際に書き込む(CSV追記 + brief.mdのマーカー付与)。

    sns_queue_approved.csvへの書き込みは追記のみ(既存行は一切変更・削除しない)。
    ファイルが存在しない場合はヘッダー行付きで新規作成する。
    """
    if not plan["to_append"]:
        return

    csv_path = plan["csv_path"]
    file_exists = os.path.exists(csv_path)
    with open(csv_path, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["slug", "lab", "text", "posted"])
        for row in plan["to_append"]:
            writer.writerow([row["slug"], row["lab"], row["text_flat"], "FALSE"])

    lines = plan["brief_lines"]
    for row in plan["to_append"]:
        i = row["line_index"]
        lines[i] = f"- [x] **{row['role']}**{_PROCESSED_MARKER}"

    with open(plan["brief_path"], "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    arg_date = sys.argv[1] if len(sys.argv) > 1 else None
    p = prepare_approval(arg_date)
    print(f"csv_path: {p['csv_path']}")
    print(f"to_append: {len(p['to_append'])} 件")
    for row in p["to_append"]:
        print(row)
