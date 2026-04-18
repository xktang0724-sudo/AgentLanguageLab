from __future__ import annotations

import os
from pathlib import Path

_HAS_LOADED_ENV_FILES = False


def load_runtime_env_files(path: str = ".env.local") -> None:
    global _HAS_LOADED_ENV_FILES

    # 避免重复加载，保证环境变量只在首次调用时写入
    if _HAS_LOADED_ENV_FILES:
        return

    env_path = Path(path)
    if env_path.exists():
        # 简单 .env 解析：跳过空行和注释，只处理 key=value
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
    # 去掉开闭一致引号，兼容 .env.local 写法
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
