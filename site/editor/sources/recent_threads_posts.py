"""
Threads自動投稿キューCSV(sns_queue.csv)から、直近投稿済み分を読み込み、
ネタ被り回避用のデータを返す関数 fetch() -> list[dict] を実装する。

- LLM呼び出しなし。純粋なファイル読み込みのみ。
- sns_queue.csv / Google Apps Script側の投稿処理には一切手を加えない(読み込み専用)。

## 現状の制約(2026-07時点)

sns_queue.csv の列は slug, lab, text, posted の4列のみで、投稿日時を示す列が無い。
また現時点では posted=TRUE の行が1件も無い(このキューはまだ実際にThreadsへ
投稿された実績がない)。

そのため、config.yaml の lookback.recent_threads_posts_days による
「直近N日」の絞り込みは、日付列が存在する場合にのみ有効になる。
日付列(posted_at または date という名前を想定)が無い場合は、日付での絞り込みは
行わず、posted=TRUE の行だけを対象にする(現状は該当0件のため空リストを返す)。

Google Apps Script側で投稿日時を記録する列が追加されたら、この関数は
コード変更なしで「直近N日分」の絞り込みを開始する。
"""

import os
import sys
import csv
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # site/editor/
from _paths import load_config, resolve_path  # noqa: E402

_DATE_COLUMN_CANDIDATES = ("posted_at", "posted_date", "date")
EXCERPT_LENGTH = 40


def _queue_csv_path():
    config = load_config()
    # config.yamlにはsns_queue.csv専用のpathsエントリが無いため、
    # site_articles.pyと同じ基準(site/)からの固定相対パスとして解決する。
    return resolve_path("sns_queue.csv")


def _find_date_column(fieldnames):
    for candidate in _DATE_COLUMN_CANDIDATES:
        if candidate in fieldnames:
            return candidate
    return None


def _parse_date(value):
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def fetch():
    """sns_queue.csv から、投稿済み(posted=TRUE)かつ直近N日以内の投稿一覧を返す。

    Returns:
        list[dict]: 各要素は {slug, lab, excerpt, posted_at}
            posted_at は日付列が無い場合 None。
    """
    config = load_config()
    lookback_days = config["lookback"]["recent_threads_posts_days"]

    csv_path = _queue_csv_path()
    if not os.path.exists(csv_path):
        print(f"WARN: {csv_path} not found, returning empty list")
        return []

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        date_column = _find_date_column(reader.fieldnames or [])

    cutoff = None
    if date_column is not None:
        cutoff = datetime.now().date() - timedelta(days=lookback_days)
    else:
        print(
            "INFO: sns_queue.csv に日付列が無いため、日付での絞り込みは行わず "
            "posted=TRUE の行のみを対象にします。"
        )

    posts = []
    for row in rows:
        if str(row.get("posted", "")).strip().upper() != "TRUE":
            continue

        posted_at = None
        if date_column is not None:
            posted_at_date = _parse_date(row.get(date_column, ""))
            if posted_at_date is None:
                continue
            if posted_at_date < cutoff:
                continue
            posted_at = posted_at_date.isoformat()

        text = row.get("text", "")
        posts.append({
            "slug": row.get("slug", ""),
            "lab": row.get("lab", ""),
            "excerpt": text[:EXCERPT_LENGTH],
            "posted_at": posted_at,
        })

    return posts


if __name__ == "__main__":
    import json
    print(json.dumps(fetch(), ensure_ascii=False, indent=2))
