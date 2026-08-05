# OpenAI Responses API 格式参考（含 DeepSeek 兼容性）

> 核对日期：2026-08-05
> 信息来源：OpenAI 官方 API 参考、DeepSeek 官方文档（链接见文末）
> 配套文档：[openai-compatible-api.md](./openai-compatible-api.md)（Chat Completions 格式基准）
> 定位：Responses API 是 OpenAI 官方推荐的新一代接口；本文作为第二协议的适配参考

## 1. 概述：双轨并行，不是替换

- Responses API 是 OpenAI 官方对新项目推荐的统一接口（`POST /v1/responses`），整合了文本/图片/文件输入、函数调用、推理、内置工具与可选的有状态会话；
- **Chat Completions 仍然存在并被广泛使用**，且是第三方兼容系（Moonshot、Ollama、vLLM、智谱等）的公共底座；
- DeepSeek 两个协议都支持：Chat Completions 全模型可用，Responses API 目前仅 `deepseek-v4-flash`；
- 结论：两者长期共存。协议层建议以 Chat Completions 为主、Responses 为第二适配目标。

## 2. 端点与公共部分

```http
POST https://api.openai.com/v1/responses
Content-Type: application/json
Authorization: Bearer <API_KEY>
```

DeepSeek 使用同一路径（OpenAI SDK 会自动拼接）：

```python
from openai import OpenAI

client = OpenAI(api_key="<key>", base_url="https://api.deepseek.com")
response = client.responses.create(
    model="deepseek-v4-flash",
    instructions="You are a helpful assistant.",
    input="Hi, how are you?",
)
print(response.output_text)
```

## 3. 顶层请求参数

| 参数 | 说明 |
| --- | --- |
| `model` | 必填，模型 ID |
| `instructions` | 系统级指令（取代 Chat Completions 的 system 消息），DeepSeek 会插入为第一条 system 消息 |
| `input` | 字符串或 input items 数组（见第 4 节）；OpenAI 至少传其一即可，DeepSeek 要求 `input` / `instructions` 至少一个 |
| `tools` | 函数工具与内置工具（见第 5 节） |
| `tool_choice` | `none` / `auto` / `required` / 指定工具（格式：`{"type": "function", "name": "..."}`） |
| `parallel_tool_calls` | 是否并行工具调用（DeepSeek 忽略，恒为并行） |
| `reasoning` | `{"effort": "low"\|"medium"\|"high"}`、`summary` 等；DeepSeek 支持 `effort`，`summary` 接受但不生成 |
| `text` | `{"format": {"type": "text"\|"json_schema", ...}}` 结构化输出；`verbosity`（DeepSeek 接受但无效） |
| `max_output_tokens` | 输出上限（取代 `max_tokens`） |
| `temperature` / `top_p` | 采样参数（DeepSeek：thinking 模式下无效） |
| `top_logprobs` | 0~20（DeepSeek 同） |
| `stream` | 布尔，事件流（见第 7 节） |
| `store` | 是否存入服务端会话（DeepSeek 不支持，恒为 `false`） |
| `previous_response_id` | 有状态续接：传上一次 response ID（DeepSeek 不支持） |
| `conversation` | 指定会话（DeepSeek 不支持） |
| `include` | 附加输出（如 web_search 来源、logprobs 等）（DeepSeek 不支持） |
| `user` | 用户标识（DeepSeek 支持） |
| `metadata` | 自定义元数据（DeepSeek 不支持） |
| `service_tier` | 服务等级（DeepSeek 不支持） |
| `background` | 后台执行（DeepSeek 不支持） |
| `prompt_cache_options` / `prompt_cache_key` | 显式缓存控制（DeepSeek 不支持，缓存自动管理） |
| `truncation` / `context_management` | 上下文截断/压缩策略（DeepSeek 不支持；超上下文直接返回 400） |
| `stream_options` | DeepSeek 不支持 |

## 4. input 格式

### 4.1 字符串快捷方式

```json
{ "model": "gpt-5.4", "input": "Tell me a story." }
```

等价于一个 `user` 角色文本消息。

### 4.2 input items 数组

```json
{
  "input": [
    {
      "type": "message",
      "role": "user",
      "content": [
        { "type": "input_text", "text": "What is in this image?" },
        { "type": "input_image", "image_url": "https://example.com/a.jpg" }
      ]
    }
  ]
}
```

常见 item 类型：

| type | 用途 | 关键字段 |
| --- | --- | --- |
| `message` | 对话消息 | `role`（user / assistant / system / developer）、`content`（字符串或 content parts） |
| `function_call` | 模型发起的工具调用（回传） | `call_id`、`name`、`arguments` |
| `function_call_output` | 工具执行结果（回传） | `call_id`、`output`（字符串） |
| `reasoning` | 模型思考过程（回传） | `content` 等 |
| `web_search_call` | 服务端搜索调用（回传） | 原样传回 |
| `computer_call` / `computer_call_output` | 电脑操作（computer use） | `call_id`、`action` 等 |

content parts：

| type | 说明 |
| --- | --- |
| `input_text` | 文本输入 |
| `input_image` | 图片（`image_url` / `file_id` / data URL） |
| `input_file` | 文件（`file_url` / `file_id` / `file_data` / `filename`） |
| `output_text` | 输出文本（回传历史时用） |

## 5. 工具定义

### 5.1 函数工具（与 Chat Completions 的差异）

`name` / `description` / `parameters` / `strict` 直接挂在工具顶层，不再嵌套 `function`：

```json
{
  "tools": [
    {
      "type": "function",
      "name": "get_current_weather",
      "description": "Get the current weather in a given location",
      "parameters": {
        "type": "object",
        "properties": {
          "location": { "type": "string" },
          "unit": { "type": "string", "enum": ["celsius", "fahrenheit"] }
        },
        "required": ["location", "unit"]
      },
      "strict": true
    }
  ],
  "tool_choice": "auto"
}
```

### 5.2 内置工具（OpenAI 服务端执行）

| type | 说明 |
| --- | --- |
| `web_search` / `web_search_preview` | 联网搜索，输出带 URL 引用（`url_citation`） |
| `file_search` | 基于 vector store 的文件检索，输出带 `file_citation` |
| `code_interpreter` | 服务端执行 Python |
| `computer_use` | 电脑操作（click / type / scroll 等 action） |
| `custom` | 自定义工具（DeepSeek 仅支持 `apply_patch`，用于 Codex 兼容） |

## 6. 响应格式

### 6.1 顶层字段

```json
{
  "id": "resp_67ca09c5...",
  "object": "response",
  "created_at": 1741294021,
  "status": "completed",
  "model": "gpt-5.4",
  "output": [],
  "output_text": "便捷字段：拼接后的完整文本",
  "parallel_tool_calls": true,
  "previous_response_id": null,
  "reasoning": { "effort": null, "summary": null },
  "store": true,
  "temperature": 1.0,
  "tool_choice": "auto",
  "tools": [],
  "top_p": 1.0,
  "usage": {
    "input_tokens": 291,
    "input_tokens_details": { "cached_tokens": 0, "cache_write_tokens": 0 },
    "output_tokens": 23,
    "output_tokens_details": { "reasoning_tokens": 0 },
    "total_tokens": 314
  }
}
```

### 6.2 output items（取代 choices）

普通文本回复：

```json
{
  "type": "message",
  "id": "msg_...",
  "status": "completed",
  "role": "assistant",
  "content": [
    {
      "type": "output_text",
      "text": "Hello! How can I help you today?",
      "annotations": []
    }
  ]
}
```

函数调用（agent 最关心）：

```json
{
  "type": "function_call",
  "id": "fc_67ca...",
  "call_id": "call_unLAR...",
  "name": "get_current_weather",
  "arguments": "{\"location\":\"Boston, MA\",\"unit\":\"celsius\"}",
  "status": "completed"
}
```

思考过程：

```json
{
  "type": "reasoning",
  "id": "rs_...",
  "summary": [],
  "content": []
}
```

### 6.3 usage 字段（与 Chat Completions 的对照）

| Chat Completions | Responses API |
| --- | --- |
| `prompt_tokens` | `input_tokens` |
| `completion_tokens` | `output_tokens` |
| `total_tokens` | `total_tokens` |
| `prompt_tokens_details.cached_tokens` | `input_tokens_details.cached_tokens` |
| `completion_tokens_details.reasoning_tokens` | `output_tokens_details.reasoning_tokens` |

DeepSeek 的 `input_tokens_details.cached_tokens` 即命中上下文缓存的 token 数。

## 7. 流式：事件流

Responses 流式是**语义事件**（SSE，`event:` + `data:`），**没有 `[DONE]` 结束标记**；每个事件带 `type`，DeepSeek 额外带递增 `sequence_number`。

典型事件序列：

```
response.created
  → response.in_progress
  → response.output_item.added        # 新增 message / function_call / reasoning item
  → response.content_part.added
  → response.output_text.delta × N    # 文本增量
  → response.output_text.done
  → response.content_part.done
  → response.output_item.done
  → response.completed                # 携带完整 response 对象与 usage
```

完整事件表：

| 事件 | 含义 |
| --- | --- |
| `response.created` | 首个事件，status 为 `in_progress` |
| `response.in_progress` | 生成中 |
| `response.output_item.added` / `.done` | output item（reasoning / message / function_call / custom_tool_call / web_search_call）开始/完成 |
| `response.content_part.added` / `.done` | content part 开始/完成 |
| `response.reasoning_text.delta` / `.done` | 思维链文本增量/完整 |
| `response.output_text.delta` / `.done` | 回答文本增量/完整 |
| `response.function_call_arguments.delta` / `.done` | 工具参数增量/完整（需拼接后 json.loads） |
| `response.custom_tool_call_input.delta` / `.done` | 自定义工具输入增量/完整 |
| `response.web_search_call.in_progress` / `.searching` / `.completed` | 服务端搜索状态 |
| `response.completed` | 正常结束，含 usage |
| `response.incomplete` | 截断结束（如达到 max_output_tokens） |
| `response.failed` | 失败结束，`error` 携带详情 |

## 8. DeepSeek Responses API 兼容性（2026-08）

### 8.1 支持范围

- 仅 `deepseek-v4-flash` 支持；`deepseek-v4-pro` 官方标注"2026 年 8 月初支持"，当前页面仍未开放；
- base_url 仍是 `https://api.deepseek.com`；
- **无状态**：`previous_response_id` / `conversation` / `store` 不支持（响应恒为 `store: false`）；
- 不支持的参数**静默忽略**，不报错——OpenAI 客户端可直接连接，但行为会打折。

### 8.2 请求参数支持矩阵

| 参数 | 状态 |
| --- | --- |
| `model` / `input` / `instructions` / `stream` | 支持 |
| `temperature`（0~2）/ `top_p` | 支持（thinking 模式无效） |
| `max_output_tokens` / `top_logprobs`（0~20） | 支持 |
| `tools`（function / web_search） | 部分支持，其他类型忽略 |
| `tool_choice` | 支持（none / auto / required / 指定工具） |
| `reasoning.effort` | 支持；`summary` 接受但不生成 |
| `text.format` | 支持；`verbosity` 无效 |
| `user` | 支持 |
| `parallel_tool_calls` / `max_tool_calls` | 忽略（恒并行） |
| `previous_response_id` / `conversation` / `store` | 不支持 |
| `background` / `metadata` / `include` / `prompt` | 不支持 |
| `truncation` | 不支持（超上下文返回 400） |
| `service_tier` / `safety_identifier` | 不支持 |
| `prompt_cache_key` / `prompt_cache_retention` / `context_management` / `stream_options` | 不支持（缓存自动管理） |

### 8.3 input items 支持矩阵

| type | 状态 |
| --- | --- |
| `message` | 支持（user / assistant / system / developer；developer 按 system 处理；content 支持字符串与 `input_text` / `output_text` parts） |
| `function_call` | 支持（合并进相邻 assistant 消息） |
| `function_call_output` | 支持 |
| `reasoning` | 支持（纯文本 content 合并进相邻 assistant 消息；summary / encrypted_content 不支持） |
| `web_search_call` | 支持（原样回传，服务端自动恢复搜索结果） |
| `input_image` / `input_file` | 不支持（不报错，图片替换为占位文本） |
| 其他类型 | 忽略 |

### 8.4 工具支持矩阵

| type | 状态 |
| --- | --- |
| `function` | 支持 |
| `web_search` / `web_search_2025_08_26` | 支持（服务端执行；`search_context_size`、`user_location` 忽略） |
| `custom` | 仅 `{"type": "custom", "name": "apply_patch"}` 支持（Codex 兼容）；其他名称返回 400 |
| `file_search` / `code_interpreter` / `computer_use` / `mcp` 等 | 忽略 |

### 8.5 其他注意

- 流式以 `response.completed` / `response.incomplete` / `response.failed` 结束，无 `[DONE]`；
- usage：`input_tokens_details.cached_tokens` 为上下文缓存命中；`output_tokens_details.reasoning_tokens` 为思维链 token；
- 响应对象兼容 OpenAI `response` 结构，不支持能力的字段取固定值（如 `store: false`、`parallel_tool_calls: true`）。

## 9. 与 Chat Completions 的快速对照

| 维度 | Chat Completions | Responses API |
| --- | --- | --- |
| 端点 | `/v1/chat/completions` | `/v1/responses` |
| system 提示 | messages 里的 system 角色 | 顶层 `instructions` |
| 输入 | `messages` 数组 | `input`（字符串或 items） |
| 输出 | `choices[0].message` | `output[]` + `output_text` |
| 工具调用 | `message.tool_calls` | `function_call` item + `function_call_output` 回传 |
| 思考过程 | DeepSeek 的 `reasoning_content` | `reasoning` item / `response.reasoning_text.delta` |
| 状态管理 | 每次全量传 | `store` + `previous_response_id` / `conversation` |
| 输出上限 | `max_tokens` / `max_completion_tokens` | `max_output_tokens` |
| usage | `prompt_tokens` / `completion_tokens` | `input_tokens` / `output_tokens` |
| 内置工具 | 无 | web_search / file_search / code_interpreter / computer_use |
| 流式结束 | `data: [DONE]` | `response.completed` / `incomplete` / `failed` |
| 工具定义 | 嵌套 `function` 对象 | 字段平铺在工具顶层 |

## 10. 对本项目（ChatModel）的适配建议

- 保持 `ChatRequest` / `ChatResponse` **语义中立**：内部统一用 Message / ToolCall / usage / finish 原因，不绑定某一协议的字段名；
- 两个协议各自写 adapter：`ChatCompletionsAdapter`（现在的主路径）+ `ResponsesAdapter`（后续）；
- adapter 负责双向映射：
  - `messages` ↔ `input`（Chat Completions 的 assistant.tool_calls 对 Responses 的 function_call + function_call_output 回传格式不同）；
  - `prompt_tokens` / `completion_tokens` ↔ `input_tokens` / `output_tokens`；
  - 流式解析器分两种：delta 聚合（Chat Completions）vs 事件状态机（Responses）；
- DeepSeek 的 Responses 是"有损兼容"（静默忽略参数），接入前先确认需要的能力在其支持矩阵内；
- 若未来要支持 Codex 工具链，DeepSeek Responses 端点是现成路径。

## 11. 参考链接

- OpenAI Responses API Reference（Create a model response）：https://developers.openai.com/api/reference/resources/responses/methods/create
- OpenAI Chat Completions Overview（含 Responses 对比入口）：https://developers.openai.com/api/reference/chat-completions/overview
- DeepSeek Using the Responses API：https://api-docs.deepseek.com/guides/responses_api
- DeepSeek Models & Pricing：https://api-docs.deepseek.com/quick_start/pricing
- DeepSeek Context Caching：https://api-docs.deepseek.com/guides/kv_cache
