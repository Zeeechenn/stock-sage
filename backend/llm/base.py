from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """
    统一 LLM 接口。
    所有调用方只依赖此接口，不直接导入具体 SDK。
    """

    @abstractmethod
    def complete_structured(
        self,
        prompt: str,
        tool: dict,
        system: str = "",
        max_tokens: int = 400,
        model_tier: str = "fast",
    ) -> dict:
        """
        发送 prompt，强制返回符合 tool['input_schema'] 的结构化 dict。
        失败时返回空 dict {}。

        tool 格式与 Anthropic tool_use 定义完全一致：
          {"name": str, "description": str, "input_schema": {JSON Schema}}

        model_tier:
          "fast"    → 低延迟低价格（Haiku / gpt-4o-mini）
          "capable" → 高能力（Sonnet / gpt-4o）
        """
