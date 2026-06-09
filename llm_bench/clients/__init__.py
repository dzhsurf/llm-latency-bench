from llm_bench.clients.anthropic_client import AnthropicClient
from llm_bench.clients.base import BaseClient, DecodeCalcConfig, StreamResult
from llm_bench.clients.openai_client import OpenAIClient


def create_client(
    api_type: str,
    base_url: str,
    api_key: str,
    model: str,
    timeout_s: float,
    decode_calc: DecodeCalcConfig | None = None,
) -> BaseClient:
    if api_type == "openai":
        return OpenAIClient(base_url, api_key, model, timeout_s, decode_calc)
    if api_type == "anthropic":
        return AnthropicClient(base_url, api_key, model, timeout_s, decode_calc)
    raise ValueError(f"Unsupported api_type: {api_type}")
