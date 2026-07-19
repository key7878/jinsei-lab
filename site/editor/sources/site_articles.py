"""
content/{lab}/*.md (frontmatter付きMarkdown) を読み込み、
existing_articles のリストを返すデータ収集層。

- LLM呼び出しなし。純粋なファイル読み込み+パースのみ。
- build.py の load_articles() と同じ方式でfrontmatterをパースする
  (正規表現 ^---\n(.*?)\n---\n(.*)$ + yaml.safe_load)。build.py自体は変更・importしない。
- 対象は content/{lab}/*.md で、lab は LABS の5つのみ(content/brand/は対象外)。
"""

import os
import re
import glob
import sys
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # site/editor/
from _paths import load_config, resolve_path  # noqa: E402

LABS = ["career", "ai", "childcare", "english", "money"]
BASE_URL = "https://mylifejinseilab.com"

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def _content_dir():
    config = load_config()
    return resolve_path(config["paths"]["content_dir"])


def fetch():
    """content/{lab}/*.md から existing_articles のリストを生成する。

    Returns:
        list[dict]: 各要素は {id, lab, title, url, published_at, tags}
    """
    content_dir = _content_dir()
    articles = []

    for lab in LABS:
        lab_dir = os.path.join(content_dir, lab)
        if not os.path.isdir(lab_dir):
            continue

        for path in sorted(glob.glob(os.path.join(lab_dir, "*.md"))):
            slug = os.path.splitext(os.path.basename(path))[0]
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()

            fm_match = _FRONTMATTER_RE.match(raw)
            if not fm_match:
                print(f"WARN: frontmatter not found in {path}, skipping")
                continue

            meta = yaml.safe_load(fm_match.group(1)) or {}

            articles.append({
                "id": f"{lab}-{slug}",
                "lab": lab,
                "title": meta.get("title", ""),
                "url": f"{BASE_URL}/labs/{lab}/{slug}",
                # YAMLの date: 2026-07-08 はPyYAMLがdatetime.dateとして
                # パースするため、スキーマ通りの文字列型に明示的に揃える。
                "published_at": str(meta.get("date", "")),
                "tags": meta.get("tags") or [],
            })

    return articles


if __name__ == "__main__":
    import json
    print(json.dumps(fetch(), ensure_ascii=False, indent=2))
