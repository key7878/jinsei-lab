"""
sources層(site_articles.fetch(), recent_threads_posts.fetch())とconfig.yamlの
静的な値を1つにまとめ、context.jsonとして書き出すための組み立てロジック。

LLM呼び出しは一切なし。
"""

import os
import sys
import json
import glob
from datetime import datetime, timedelta, timezone

_EDITOR_DIR = os.path.dirname(os.path.abspath(__file__))  # site/editor/
sys.path.insert(0, _EDITOR_DIR)
sys.path.insert(0, os.path.join(_EDITOR_DIR, "sources"))

from _paths import load_config, resolve_path  # noqa: E402
import site_articles  # noqa: E402
import recent_threads_posts  # noqa: E402

JST = timezone(timedelta(hours=9))
CONTEXT_PATH = os.path.join(_EDITOR_DIR, "context.json")

# theme_decision.json のスキーマは2026-07-19時点で未確定(1件も存在しない)。
# 想定形: { "theme_id": "...", "decided_at": "2026-07-19", ... }
# 日付キーは decided_at / created_at / date のいずれかを想定し、
# 無い・パースできない場合はエラーにせず警告してスキップする。
_THEME_ID_DATE_KEYS = ("decided_at", "created_at", "date")


def _collect_recent_theme_ids(config):
    """editor/drafts/ 配下のtheme_decision.jsonから、lookback期間内のtheme_idを集める。

    editor/drafts/ が存在しない、またはtheme_decision.jsonが1件も無い場合は
    エラーにせず静かに空リストを返す(2026-07-19時点の実際の状態)。
    """
    drafts_dir = resolve_path(config["paths"]["drafts_dir"])
    if not os.path.isdir(drafts_dir):
        return []

    lookback_days = config["lookback"]["recent_theme_ids_days"]
    cutoff = datetime.now().date() - timedelta(days=lookback_days)

    theme_ids = []
    pattern = os.path.join(drafts_dir, "**", "theme_decision.json")
    for path in sorted(glob.glob(pattern, recursive=True)):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"WARN: failed to read {path}: {e}, skipping")
            continue

        theme_id = data.get("theme_id")
        if not theme_id:
            print(f"WARN: {path} has no theme_id, skipping")
            continue

        date_value = next((data[k] for k in _THEME_ID_DATE_KEYS if k in data), None)
        if date_value is None:
            print(f"WARN: {path} has no recognizable date field, skipping")
            continue

        try:
            decided_date = datetime.strptime(str(date_value)[:10], "%Y-%m-%d").date()
        except ValueError:
            print(f"WARN: {path} has unparseable date {date_value!r}, skipping")
            continue

        if decided_date >= cutoff:
            theme_ids.append(theme_id)

    return theme_ids


def build_context():
    """existing_articles / recent_threads_posts / config.yamlの静的値を1つにまとめる。

    Returns:
        dict: context.jsonの内容そのもの
    """
    config = load_config()

    return {
        "generated_at": datetime.now(JST).isoformat(timespec="seconds"),
        "existing_articles": site_articles.fetch(),
        "recent_threads_posts": recent_threads_posts.fetch(),
        "recent_theme_ids": _collect_recent_theme_ids(config),
        "lab_focus_weights": config["lab_focus_weights"],
        "constraints": {
            "prohibited_hype_words": config["prohibited_hype_words"],
        },
    }


def write_context(context=None):
    """build_context()の結果を site/editor/context.json へ上書き書き出す。

    実行するたびに上書きする(履歴は残さない)。

    Returns:
        str: 書き出したファイルの絶対パス
    """
    if context is None:
        context = build_context()
    with open(CONTEXT_PATH, "w", encoding="utf-8") as f:
        json.dump(context, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return CONTEXT_PATH


if __name__ == "__main__":
    print(json.dumps(build_context(), ensure_ascii=False, indent=2))
