import inspect
import json
from pydantic import BaseModel, Field
from typing import get_type_hints, Any, Callable
from ..models.types import ToolCall


def get_weather(location: str) -> str:
    return json.dumps({"location": location, "temperature_c": 24, "condition": "sunny"})


_TYPE_MAP = {
    str: "string", int: "integer", float: "number",
    bool: "boolean", list: "array", dict: "object"
}


def fn_to_tool_schema(fn: Callable) -> dict:
    sig = inspect.signature(fn)
    hints = get_type_hints(fn)
    props: dict = {}
    required: list[str] = []
    for name, p in sig.parameters.items():
        if name in ("self", "cls") or p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            continue
        t = hints.get(name, Any)
        props[name] = {"type": _TYPE_MAP.get(t, "string")}
        if p.default is p.empty:
            required.append(name)
        elif p.default is not None:
            props[name]["default"] = p.default

    doc = inspect.getdoc(fn) or ""
    description = doc.strip().splitlines()[0] if doc.strip() else fn.__name__

    TOOL = {
        "type": "function",
        "function": {
            "name": fn.__name__,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": props,
                "required": required,
            }
        }
    }
    return TOOL


class ToolRegister():
    def __init__(self):
        self._tools: dict[str, Callable] = {}
        self._schemas: list[dict] = []

    def register(self, fn: Callable) -> None:
        self._tools[fn.__name__] = fn
        self._schemas.append(fn_to_tool_schema(fn))

    def schema(self) -> list[dict]:
        return self._schemas

    def execute(self, tc: ToolCall) -> str:
        fn = self._tools.get(tc.name)
        if fn is None:
            return f"工具不存在: {tc.name}"
        try:
            return str(fn(**tc.arguments))
        except Exception as e:
            return f"工具{tc.name}执行失败: {e}"
