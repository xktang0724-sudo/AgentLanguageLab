from __future__ import annotations

from dataclasses import fields, is_dataclass
from types import MappingProxyType
from typing import Any, Mapping


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {
            field.name: to_jsonable(getattr(value, field.name))
            for field in fields(value)
        }

    if isinstance(value, MappingProxyType):
        return {key: to_jsonable(item) for key, item in value.items()}

    if isinstance(value, Mapping):
        return {key: to_jsonable(item) for key, item in value.items()}

    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]

    if isinstance(value, list):
        return [to_jsonable(item) for item in value]

    return value
