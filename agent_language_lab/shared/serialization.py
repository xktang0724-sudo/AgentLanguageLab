from __future__ import annotations

from dataclasses import fields, is_dataclass
from types import MappingProxyType
from typing import Any, Mapping


def to_jsonable(value: Any) -> Any:
    # dataclass -> dict，递归处理，避免 JSON 直接序列化失败
    if is_dataclass(value):
        return {
            field.name: to_jsonable(getattr(value, field.name))
            for field in fields(value)
        }

    # MappingProxyType 与 Mapping 都统一展开成普通 dict
    if isinstance(value, MappingProxyType):
        return {key: to_jsonable(item) for key, item in value.items()}

    if isinstance(value, Mapping):
        return {key: to_jsonable(item) for key, item in value.items()}

    # 元组转列表，保持 JSON 兼容；列表也逐层处理元素
    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]

    if isinstance(value, list):
        return [to_jsonable(item) for item in value]

    return value
