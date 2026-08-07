from .deepseek import DeepSeekProvider
from ..models.chat_model import ChatModel


def get_provider(provider_name: str) -> ChatModel:
    if provider_name == "deepseek":
        return DeepSeekProvider()
    raise ValueError(f"provider {provider_name} not found")
