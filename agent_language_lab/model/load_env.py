from __future__ import annotations

import os
from pathlib import Path

_HAS_LOADED_ENV_FILES = False


def load_runtime_env_files(path: str = ".env.local") -> None:
    global _HAS_LOADED_ENV_FILES

    if _HAS_LOADED_ENV_FILES:
        return

    env_path = Path(path)
    if env_path.exists():
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, raw_value = line.split("=", 1)
            key = key.strip()
            value = strip_optional_quotes(raw_value.strip())
            os.environ.setdefault(key, value)

    _HAS_LOADED_ENV_FILES = True


def strip_optional_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
