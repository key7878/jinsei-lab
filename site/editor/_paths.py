"""
site/editor/ 配下の各モジュールで共通して使う、config.yaml読み込みとパス解決のヘルパー。

config.yaml自身の位置(このファイルと同じ site/editor/)から site/ を導出するため、
実行時のカレントディレクトリに依存しない。
"""

import os
import yaml

EDITOR_DIR = os.path.dirname(os.path.abspath(__file__))  # site/editor/
SITE_DIR = os.path.dirname(EDITOR_DIR)                     # site/
CONFIG_PATH = os.path.join(EDITOR_DIR, "config.yaml")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_path(relative_path):
    """config.yaml内の相対パス(site/を基準とする記述)を、site/からの絶対パスに解決する。"""
    return os.path.normpath(os.path.join(SITE_DIR, relative_path))
