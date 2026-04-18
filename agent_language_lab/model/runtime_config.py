from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal, Mapping, TypeAlias

ModelRuntimeEnvironment: TypeAlias = Mapping[str, str]
AgentModelMode: TypeAlias = Literal["demo", "dev"]
SupportedModelProvider: TypeAlias = Literal["openai", "anthropic"]


@dataclass(frozen=True, slots=True)
class DemoRuntimeModelConfig:
    mode: Literal["demo"] = "demo"


@dataclass(frozen=True, slots=True)
class DevRuntimeModelConfig:
    model_id: str
    provider: SupportedModelProvider
    model_name: str
    api_key: str
    base_url: str | None = None
    mode: Literal["dev"] = "dev"


RuntimeModelConfig: TypeAlias = DemoRuntimeModelConfig | DevRuntimeModelConfig


# 按环境变量构建运行时模型配置：demo 模式降级为本地模型，dev 模式预留校验后暂不支持
def read_runtime_model_config(
    env: ModelRuntimeEnvironment | None = None,
) -> RuntimeModelConfig:
    active_env = os.environ if env is None else env
    mode = read_agent_model_mode(active_env)
    if mode == "demo":
        return DemoRuntimeModelConfig()

    provider, model_name, model_id = parse_model_id(read_required_model_id(active_env))
    api_key_name = "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
    api_key = read_required_env(active_env, api_key_name)

    return DevRuntimeModelConfig(
        model_id=model_id,
        provider=provider,
        model_name=model_name,
        api_key=api_key,
        base_url=read_optional_base_url(active_env, provider),
    )


# 读取并校验模式：默认 demo，不允许其他模式穿透
def read_agent_model_mode(
    env: ModelRuntimeEnvironment | None = None,
) -> AgentModelMode:
    active_env = os.environ if env is None else env
    mode = active_env.get("AGENT_MODEL_MODE", "demo")
    if mode in {"demo", "dev"}:
        return mode

    raise ValueError(
        f'Unsupported AGENT_MODEL_MODE: {mode}. Expected "demo" or "dev".'
    )


# 解析 provider:model 形式，分离出 provider 与 model_name，保留完整 model_id
def parse_model_id(model_id: str) -> tuple[SupportedModelProvider, str, str]:
    separator_index = model_id.find(":")
    if separator_index <= 0 or separator_index == len(model_id) - 1:
        raise ValueError(
            f'Invalid AGENT_MODEL_ID: {model_id}. Expected "<provider>:<model-name>".'
        )

    provider = model_id[:separator_index]
    model_name = model_id[separator_index + 1 :]
    if provider not in {"openai", "anthropic"}:
        raise ValueError(
            f'Unsupported AGENT_MODEL_ID provider: {provider}. '
            'Expected "openai" or "anthropic".'
        )

    return provider, model_name, model_id


def read_required_model_id(env: ModelRuntimeEnvironment) -> str:
    # dev 模式必须提供 AGENT_MODEL_ID
    return read_required_env(
        env,
        "AGENT_MODEL_ID",
        "AGENT_MODEL_MODE=dev requires AGENT_MODEL_ID to be set.",
    )


def read_required_env(
    env: ModelRuntimeEnvironment,
    key: str,
    message: str | None = None,
) -> str:
    # 读取环境变量并在缺失时给出明确错误信息
    value = env.get(key)
    if value:
        return value

    raise ValueError(message or f"{key} must be set.")


# 返回 provider 级或通用 base url，优先 AGENT_MODEL_BASE_URL 再回退 provider 专有变量
def read_optional_base_url(
    env: ModelRuntimeEnvironment,
    provider: SupportedModelProvider,
) -> str | None:
    generic_base_url = env.get("AGENT_MODEL_BASE_URL")
    if generic_base_url:
        return generic_base_url

    provider_key = "OPENAI_BASE_URL" if provider == "openai" else "ANTHROPIC_BASE_URL"
    return env.get(provider_key)
