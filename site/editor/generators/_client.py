"""
config.yamlのgenerator.modeに応じてLLM呼び出しを切り替えるクライアント層。
"""

import os
import sys
import subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))         # site/editor/generators/
sys.path.insert(0, os.path.dirname(_HERE))                  # site/editor/
from _paths import load_config, SITE_DIR  # noqa: E402

_TIMEOUT_SECONDS = 180


def _call_claude_code(prompt: str) -> str:
    """Claude Code CLIの非対話モード(`claude -p`)でpromptを実行し、テキスト出力を返す。

    採用しているフラグ:
      -p / --print          : 対話REPLに入らず、1回の応答を返して終了する非対話モード。
      --output-format text  : アシスタントの最終テキストのみを返す(既定値だが明示)。

    promptにはGUIDELINES.md/HARU.md/context.jsonの内容がすべて文字列として
    展開済みで、ファイル読み込み等のツール呼び出しを一切必要としない
    (テキスト入出力のみ)。そのため --dangerously-skip-permissions は使わない。
    このプロセスにはTTYが無く許可プロンプトに応答できないが、そもそも
    許可を要するツール呼び出しが発生しない設計にすることで解決している。

    プロンプトは引数ではなくstdin経由で渡す(長文のため、OSの引数長制限や
    シェルエスケープの問題を避ける)。
    """
    try:
        result = subprocess.run(
            ["claude", "-p", "--output-format", "text"],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=SITE_DIR,
            timeout=_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as e:
        raise RuntimeError(
            "`claude` CLIが見つかりません。PATHが通っているか確認してください。"
        ) from e
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"claude -p が{_TIMEOUT_SECONDS}秒でタイムアウトしました。") from e

    if result.returncode != 0:
        raise RuntimeError(
            f"claude -p failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout


def call_llm(prompt: str) -> str:
    """config.yamlのgenerator.modeに応じてLLMを呼び出し、テキスト出力を返す。"""
    config = load_config()
    mode = config["generator"]["mode"]

    if mode == "claude_code":
        return _call_claude_code(prompt)
    if mode in ("api", "manual"):
        raise NotImplementedError(f"generator.mode={mode!r} はまだ未実装です")
    raise ValueError(f"unknown generator.mode: {mode!r}")
