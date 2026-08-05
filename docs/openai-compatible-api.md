# OpenAI 兼容系 Chat Completions 格式参考

> 核对日期：2026-08-05
> 信息来源：OpenAI 官方 API 参考、DeepSeek 官方文档（链接见文末）
> 用途：作为本项目 `ChatModel` 协议与 provider 适配层的格式基准

## 1. 什么是"OpenAI 兼容系"

以 `POST /chat/completions` 为核心接口、请求/响应结构与 OpenAI Chat Completions API 一致的模型服务。共同特征：

- 用 OpenAI 官方 SDK 改 `base_url` + `api_key` 即可接入；
- `messages` / `tools` / 响应结构相同；
- 各家在核心之上有扩展字段（如 DeepSeek 的 `thinking`、`reasoning_content`）。

常见成员（端点以各家官方文档为准）：

| 服务 | base_url / 端点 | 备注 |
| --- | --- | --- |
| OpenAI | `https://api.openai.com/v1` | 格式源头；官方新项目推荐 Responses API |
| DeepSeek | `https://api.deepseek.com` | 另有 `/anthropic`、`/beta` 两个变体端点 |
| Moonshot Kimi | `https://api.moonshot.cn/v1` | OpenAI 兼容 |
| 阿里云 DashScope | `https://dashscope.aliyuncs.com/compatible-mode/v1` | 兼容模式 |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4` | |
| SiliconFlow | `https://api.siliconflow.cn/v1` | |
| OpenRouter | `https://openrouter.ai/api/v1` | 多模型聚合 |
| Ollama（本地） | `http://localhost:11434/v1` | 本地模型 |
| vLLM / llama.cpp / LM Studio | `http://localhost:<port>/v1` | 自托管推理 |

## 2. 请求格式

### 2.1 公共部分

```http
POST https://api.deepseek.com/chat/completions
Content-Type: application/json
Authorization: Bearer <API_KEY>
```

注意：OpenAI SDK 会自动在 `base_url` 后拼接 `/chat/completions`，所以 DeepSeek 的 `base_url` 填 `https://api.deepseek.com` 即可（不要带 `/v1`）。

### 2.2 核心参数对比

| 参数 | OpenAI | DeepSeek | 说明 |
| --- | --- | --- | --- |
| `model` | 必填 | 必填 | 模型 ID |
| `messages` | 必填 | 必填 | 对话消息数组 |
| `tools` | 可选 | 可选 | 函数工具列表（最多 128 个） |
| `tool_choice` | `none` / `auto` / `required` / 指定工具 | 同左 | 无 tools 时默认 `none`，有 tools 时默认 `auto` |
| `temperature` | 0~2，默认 1 | 同左 | 与 `top_p` 建议只改其一 |
| `top_p` | 0~1，默认 1 | 同左 | nucleus sampling |
| `max_tokens` | 已弃用（用 `max_completion_tokens`） | 支持 | 输出 token 上限 |
| `max_completion_tokens` | 支持（含 reasoning tokens） | 未提及 | OpenAI 新参数 |
| `stop` | 最多 4 个序列 | 最多 16 个序列 | 停止序列 |
| `stream` | 布尔 | 同左 | SSE 流式 |
| `stream_options.include_usage` | 支持 | 支持 | 流式末尾追加 usage chunk |
| `response_format` | `text` / `json_object` / `json_schema` | `text` / `json_object` | 结构化输出 |
| `logprobs` / `top_logprobs` | 支持 | 支持 | 对数概率（DeepSeek 未在参考页列出，但格式同左） |
| `seed` | 支持 | 未提及 | 复现采样 |
| `frequency_penalty` / `presence_penalty` | 支持 | 已弃用（传了也不生效） | DeepSeek 明确标注 deprecated |
| `user` / `user_id` | `user` | `user_id` | 用户标识；DeepSeek 用于内容安全、KVCache 与调度隔离 |
| `thinking` | — | `{"type": "enabled"\|"disabled"}` | DeepSeek 思维模式开关，默认 `enabled` |
| `reasoning_effort` | `low`/`medium`/`high` 等 | `low`/`high`/`max`（默认 `high`） | 推理强度 |

## 3. messages 消息格式

### 3.1 role 一览

| role | OpenAI | DeepSeek | 关键字段 |
| --- | --- | --- | --- |
| `system` | 支持（新推理模型建议改用 developer） | 支持 | `content` |
| `developer` | 支持（o1 及更新） | 不支持 | `content` |
| `user` | 支持 | 支持 | `content`（字符串或 content parts 数组） |
| `assistant` | 支持 | 支持 | `content`（可 null）、`tool_calls`、`reasoning_content`（DeepSeek） |
| `tool` | 支持 | 支持 | `tool_call_id` 必填 |
| `function` | 已弃用 | 不支持 | 旧版函数调用 |

### 3.2 完整示例（含工具调用多轮）

```json
{
  "model": "deepseek-v4-pro",
  "messages": [
    { "role": "system", "content": "You are a helpful assistant." },
    { "role": "user", "content": "How's the weather in Hangzhou?" },
    {
      "role": "assistant",
      "content": null,
      "tool_calls": [
        {
          "id": "call_abc123",
          "type": "function",
          "function": { "name": "get_weather", "arguments": "{\"location\": \"Hangzhou\"}" }
        }
      ]
    },
    { "role": "tool", "tool_call_id": "call_abc123", "content": "24℃" }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get weather of a location",
        "parameters": {
          "type": "object",
          "properties": { "location": { "type": "string" } },
          "required": ["location"]
        }
      }
    }
  ],
  "tool_choice": "auto"
}
```

要点：

- 工具多轮必须把带 `tool_calls` 的 assistant 消息原样回传，再追加对应 `tool` 消息；
- `tool_call_id` 一一对应；
- `function.arguments` 是 **JSON 字符串**，不是对象，需要 `json.loads`；
- 文档明确警告：模型不保证生成合法 JSON，调用前必须校验。

## 4. tools 与 tool calling

### 4.1 工具定义

```json
{
  "type": "function",
  "function": {
    "name": "get_weather",
    "description": "Get weather of a location, the user should supply a location first.",
    "parameters": {
      "type": "object",
      "properties": {
        "location": { "type": "string", "description": "The city and state, e.g. San Francisco, CA" }
      },
      "required": ["location"]
    }
  }
}
```

### 4.2 tool_choice

- `"none"`：不调用工具；
- `"auto"`：模型自行决定（默认）；
- `"required"`：必须调用工具；
- `{"type": "function", "function": {"name": "get_weather"}}`：强制指定工具。

### 4.3 响应中的 tool_calls

```json
{
  "id": "call_abc123",
  "type": "function",
  "function": { "name": "get_weather", "arguments": "{\"location\": \"Hangzhou\"}" }
}
```

对应 `finish_reason` 为 `tool_calls`。

### 4.4 DeepSeek strict 模式（Beta）

- 需使用 `base_url = "https://api.deepseek.com/beta"`；
- 所有 `function` 需设置 `"strict": true`；
- 服务端校验 JSON Schema，不合法直接报错；
- 限制：所有 `object` 属性必须 `required`、`additionalProperties` 必须 `false`；
- 支持类型：`object` / `string` / `number` / `integer` / `boolean` / `array` / `enum` / `anyOf`；
- `string` 支持 `pattern`、`format`（email/hostname/ipv4/ipv6/uuid），不支持 minLength/maxLength；
- 支持 `$def` + `$ref` 复用与递归。

## 5. 非流式响应

```json
{
  "id": "930c60df-bf64-41c9-a88e-3ec75f81e00e",
  "object": "chat.completion",
  "created": 1705651092,
  "model": "deepseek-v4-pro",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you today?"
      },
      "logprobs": null,
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 16,
    "completion_tokens": 10,
    "total_tokens": 26
  },
  "system_fingerprint": "fp_a49d71b8a1"
}
```

### 5.1 顶层字段

| 字段 | 说明 |
| --- | --- |
| `id` | 完成 ID |
| `object` | `chat.completion`（流式是 `chat.completion.chunk`） |
| `created` | Unix 时间戳 |
| `model` | 实际使用的模型 |
| `choices[]` | 候选结果（通常 1 个） |
| `usage` | token 统计 |
| `system_fingerprint` | 后端配置指纹 |

### 5.2 finish_reason 对比

| 取值 | OpenAI | DeepSeek | 含义 |
| --- | --- | --- | --- |
| `stop` | ✓ | ✓ | 自然停止或命中 stop 序列 |
| `length` | ✓ | ✓ | 达到 token 上限 |
| `tool_calls` | ✓ | ✓ | 模型请求调用工具 |
| `content_filter` | ✓ | ✓ | 内容被过滤 |
| `function_call` | ✓（弃用） | ✗ | 旧版函数调用 |
| `insufficient_system_resource` | ✗ | ✓ | 推理系统资源不足中断 |

### 5.3 usage 对比

| 字段 | OpenAI | DeepSeek |
| --- | --- | --- |
| `prompt_tokens` | ✓ | ✓ |
| `completion_tokens` | ✓ | ✓ |
| `total_tokens` | ✓ | ✓ |
| `prompt_tokens_details.cached_tokens` | ✓ | ✗ |
| `prompt_tokens_details.cache_write_tokens` | ✓ | ✗ |
| `prompt_cache_hit_tokens` / `prompt_cache_miss_tokens` | ✗ | ✓（自动上下文缓存） |
| `completion_tokens_details.reasoning_tokens` | ✓ | ✓ |

### 5.4 DeepSeek 特有：reasoning_content

Thinking 模式下，assistant 消息在 `content` 之外还会返回：

```json
{
  "message": {
    "role": "assistant",
    "content": "最终回答",
    "reasoning_content": "模型思考过程"
  }
}
```

## 6. 流式响应（SSE）

以 `data: ` 前缀逐块推送 JSON，结束标记：

```
data: [DONE]
```

chunk 结构：

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion.chunk",
  "created": 1694268190,
  "model": "gpt-4o-mini",
  "choices": [
    {
      "index": 0,
      "delta": { "role": "assistant", "content": "Hello" },
      "logprobs": null,
      "finish_reason": null
    }
  ]
}
```

要点：

- 首个 chunk 的 `delta` 带 `role`，后续只带增量 `content`；
- 最后一个 chunk 的 `finish_reason` 变为 `stop` 等，`delta` 为空；
- 工具调用是**分片增量**，需要按 `index` 聚合 `delta.tool_calls[]`，其中 `id`、`name` 只在首片出现，`arguments` 按片拼接；
- DeepSeek thinking 模式下，流式 `delta` 还包含 `reasoning_content` 增量；
- 设置 `"stream_options": {"include_usage": true}` 后，`[DONE]` 前会多一个 usage chunk（`choices` 为空数组），OpenAI 与 DeepSeek 行为一致。

## 7. JSON 输出

```json
{
  "response_format": { "type": "json_object" }
}
```

- OpenAI 另有 `json_schema` + `strict: true` 的 Structured Outputs；
- DeepSeek 官方警告：使用 JSON Output 时**必须在 system/user 消息里显式要求输出 JSON**，否则模型可能一直生成空白直到 token 上限；
- 若 `finish_reason == "length"`，JSON 可能被截断，需要检测并重试。

## 8. DeepSeek 现状（2026-08）

### 8.1 模型

| 模型 ID | 版本 | 上下文 | 最大输出 | 说明 |
| --- | --- | --- | --- | --- |
| `deepseek-v4-flash` | DeepSeek-V4-Flash-0731 | 1M | 384K | 默认 thinking；支持 Responses API |
| `deepseek-v4-pro` | DeepSeek-V4-Pro | 1M | 384K | 默认 thinking；暂不支持 Responses API |

### 8.2 Thinking Mode

```json
{
  "thinking": { "type": "enabled" },
  "reasoning_effort": "high"
}
```

- `thinking.type`：`enabled`（默认）/ `disabled`；
- `reasoning_effort`：`low` / `high` / `max`，默认 `high`；`medium`、`xhigh` 会映射到 `high`；
- 官方注明：目前 flash 支持三档；pro 暂时只支持 `high` / `max`（`low`→`high`、`xhigh`→`max`），预计 2026 年 8 月初全量支持；
- thinking 模式下同样支持工具调用（V3.2 起）。

### 8.3 端点变体

| base_url | 用途 |
| --- | --- |
| `https://api.deepseek.com` | OpenAI 兼容（默认） |
| `https://api.deepseek.com/anthropic` | Anthropic 格式 |
| `https://api.deepseek.com/beta` | Beta 功能：strict 工具、Chat Prefix Completion |

Chat Prefix Completion（Beta）：assistant 消息带 `"prefix": true` 强制模型以指定前缀开头，可配合 `reasoning_content` 注入思维链输入。

### 8.4 价格（每 1M tokens）

| 模型 | 输入（缓存命中） | 输入（未命中） | 输出 |
| --- | --- | --- | --- |
| deepseek-v4-flash | $0.0028 | $0.14 | $0.28 |
| deepseek-v4-pro | $0.003625 | $0.435 | $0.87 |

官方预告：近期将实行峰谷定价，高峰时段（北京时间 9:00–12:00、14:00–18:00）价格 x2。

## 9. 错误格式

两家错误体结构一致：

```json
{
  "error": {
    "message": "错误描述",
    "type": "错误类型",
    "param": null,
    "code": "错误码"
  }
}
```

DeepSeek HTTP 状态码：

| 状态码 | 含义 | 处理建议 |
| --- | --- | --- |
| 400 | Invalid Format，请求体格式错误 | 按提示修正 |
| 401 | Authentication Fails，API key 错误 | 检查 key |
| 402 | Insufficient Balance，余额不足 | 充值 |
| 422 | Invalid Parameters | 修正参数 |
| 429 | Rate Limit Reached | 限速退避 |
| 500 | Server Error | 短暂等待后重试 |
| 503 | Server Overloaded | 退避重试 |

OpenAI 常见 code（供映射）：`invalid_api_key`、`insufficient_quota`、`rate_limit_exceeded`、`context_length_exceeded`、`invalid_request_error` 等。

## 10. 适配到本项目 ChatModel 的建议映射

```text
ChatRequest.messages        -> 请求 messages
ChatRequest.tools           -> 请求 tools
ChatRequest.tool_choice     -> 请求 tool_choice
ChatRequest.temperature 等  -> 请求采样参数（可选覆盖）

ChatResponse.content        <- choices[0].message.content
ChatResponse.tool_calls     <- choices[0].message.tool_calls
ChatResponse.finish_reason  <- choices[0].finish_reason
ChatResponse.usage          <- usage（保留厂商原始字段）
ChatResponse.reasoning      <- message.reasoning_content（DeepSeek 可选）
```

设计注意：

- `arguments` 存字符串，解析与校验放 provider 层之外（agent 层）；
- 流式与工具调用聚合逻辑放 provider 实现内部，协议层只暴露结果；
- `usage` 建议保留原始 dict 并提取公共字段，避免各家 `cached_tokens` / `prompt_cache_hit_tokens` 差异外溢；
- 错误统一映射为项目异常（`RateLimitError` ↔ 429，`ContextLengthError` ↔ 422/context_length_exceeded）。

## 11. 参考链接

- OpenAI Chat Completions API Reference：https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create
- OpenAI Chat Completions Overview：https://developers.openai.com/api/reference/chat-completions/overview
- DeepSeek Chat Completions API：https://api-docs.deepseek.com/api/create-chat-completion
- DeepSeek Models & Pricing：https://api-docs.deepseek.com/quick_start/pricing
- DeepSeek Thinking Mode：https://api-docs.deepseek.com/guides/thinking_mode
- DeepSeek Tool Calls：https://api-docs.deepseek.com/guides/tool_calls
- DeepSeek Error Codes：https://api-docs.deepseek.com/quick_start/error_codes
