from app.agents.tools import fn_to_tool_schema
from pydantic import Field, BaseModel
import json


class WeatherArgs(BaseModel):
    location: str = Field(description="城市或国家")


def get_weather(location: str) -> str:
    """根据 location 获取天气信息。"""
    return json.dumps({"location": location, "temperature_c": 24, "condition": "sunny"})


def test_fn_to_tool_schema():
    print(fn_to_tool_schema(get_weather))
    print(WeatherArgs.model_json_schema())
