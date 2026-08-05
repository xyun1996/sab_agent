# Agent 开发知识清单（OpenAI 兼容协议视角）

> 整理日期：2026-08-05
> 配套文档：[openai-compatible-api.md](./openai-compatible-api.md)（协议格式基准）
> 定位：从"会调 API"到"能写 agent"的知识缺口清单，按主题分块，标注每块影响项目哪部分代码

## 1. 流式（SSE）

### 1.1 协议层要点

- SSE 解析：按行读 `data: ` 前缀的 JSON，空行分隔事件，`data: [DONE]` 收尾；
- SSE 没有自动重连，断流必须由客户端处理；
- `delta.content` 逐片拼接成完整内容；
- `delta.tool_calls` 按 `index` 分片聚合：`id`、`name` 只在首片出现，`arguments` 是增量片段，需要拼接后整体 `json.loads`；
- DeepSeek thinking 模式还有 `delta.reasoning_content` 增量；
- `"stream_options": {"include_usage": true}` 时，`[DONE]` 前会多一个 usage chunk，其 `choices` 为空数组（OpenAI / DeepSeek 行为一致）；
- 最后一个 chunk 的 `finish_reason` 从 `null` 变为实际值。

### 1.2 工程层要点

- 取消与超时：`asyncio` 下取消生成器要干净；连接超时、首包超时、总时长分开配置；
- 半开连接：收到部分数据后连接断开，聚合逻辑必须容忍"没有 `[DONE]` 就结束"；
- 错误可能出现在 200 之后（流中途断开），不能假设流式一定完整；
- 如果后续要做 UI 流式输出，需要把"字节级事件流"转成"文本增量"再上推。

## 2. Agent 循环

这是从"API 封装"到"agent"的分水岭，核心是工具调用闭环：

1. 请求（带 `tools`）；
2. 响应含 `message.tool_calls`（`finish_reason == "tool_calls"`）；
3. 执行工具；
4. 把带 `tool_calls` 的 assistant 消息**原样回传**，再追加 `tool` 角色消息（`tool_call_id` 一一对应）；
5. 再次请求，直到 `finish_reason == "stop"`。

### 2.1 必须处理的边界

- **最大迭代上限**：`max_iterations`，否则工具结果循环触发时死循环；
- **工具异常**：工具抛错要以 `tool` 消息回传给模型（内容写错误信息），让模型自我纠正，而不是中断对话；
- **并行工具调用**：OpenAI 有 `parallel_tool_calls` 参数（默认 true）；DeepSeek 无此参数。按"一次响应可能有多个 tool_calls，逐个执行、全部回传"编写，兼容两者；
- **终止条件**：`finish_reason == "stop"`、达到最大轮数、上下文超限，三选一都要优雅退出；
- **强制工具**：`tool_choice` 支持 `none` / `auto` / `required` / 指定工具名，`required` 用于必须调用工具的场景；
- **参数校验**：`function.arguments` 是 JSON 字符串且模型不保证合法，执行前必须校验；`strict` 模式（DeepSeek Beta）可减少非法输出但有限制。

## 3. 上下文与 token 管理

agent 对话一长必然遇到，是稳定性关键：

- **token 估算**：用 tiktoken（OpenAI）或各家 tokenizer 估算，用于裁剪决策；
- **消息配对完整性**：裁剪历史时 `assistant.tool_calls` 与对应 `tool` 消息必须成对删除，只删一半请求直接报错；
- **稳定前缀**：system prompt + 工具定义放最前面且尽量保持不变——DeepSeek 自动命中上下文缓存（`prompt_cache_hit_tokens`），OpenAI 也有 prompt caching，前缀稳定直接降本；
- **超长策略**：滑动窗口丢最旧消息、摘要压缩、或按 `context_length_exceeded` 错误触发裁剪后重试；
- **不回传思考内容**：DeepSeek 的 `reasoning_content` 不需要（也不建议）塞回历史；
- **工具定义体积**：工具多了 JSON Schema 本身吃上下文，考虑动态加载/按需注入工具。

## 4. 推理模型行为差异

2026 年主流模型普遍带思考能力，协议层要兼容这些差异：

- `reasoning_content` 不计入 `content`，但计入计费（`completion_tokens_details.reasoning_tokens`）；
- 部分推理模型不支持 `temperature` / `top_p`（OpenAI o 系/5.x 部分忽略或报错），DeepSeek 已弃用 `frequency_penalty` / `presence_penalty`——协议层只传两家都支持的公共子集；
- `max_completion_tokens`（含推理 token，OpenAI 新）vs `max_tokens`（OpenAI 已弃用、DeepSeek 仍用）是兼容坑，按 provider 分别映射；
- DeepSeek thinking 开关：`thinking: {"type": "enabled"|"disabled"}`，`reasoning_effort: low|high|max`（默认 high；pro 当前只支持 high/max）；
- 思考内容可能含敏感信息，日志必须脱敏；
- 流式场景思考与回答分两个阶段输出，UI 上可能要分开展示。

## 5. 错误、重试与限流

### 5.1 重试矩阵

| 状态码/错误 | 是否重试 | 策略 |
| --- | --- | --- |
| 400 / 401 / 402 / 422 | 否 | 修正请求或提示用户 |
| 429 Rate Limit | 是 | 指数退避 + jitter，参考 `Retry-After` |
| 500 / 503 | 是 | 退避重试，次数上限 |
| `context_length_exceeded` | 是（特殊） | 裁剪上下文后重试，不能无脑重试 |

### 5.2 其他要点

- 超时分三级：连接、首包、总时长；
- **重试副作用**：工具执行可能有副作用（扣费/下单），重试应只覆盖"请求模型"阶段，工具执行尽量幂等；
- 错误体解析：`error.message / type / code / param`，映射到项目异常层级（`ProviderError`、`RateLimitError`、`ContextLengthError`、`TimeoutError`）；
- 并发控制：`asyncio.Semaphore` 限并发，参考各家并发上限（DeepSeek flash 2500 / pro 500）；
- 流式重试注意：半途断流的请求可能已产生费用，重试前评估成本。

## 6. 协议兼容性设计与趋势

- **最小公共子集原则**：协议层只依赖各家都有的字段，厂商扩展（`thinking`、`reasoning_content`、`user_id`、`prompt_cache_hit_tokens`）走可选字段，不进核心接口；
- **Responses API**：OpenAI 新方向（有状态、统一工具/推理/结构化输出），DeepSeek flash 已支持但 pro 未支持——agent 框架可留意，兼容系主力仍是 Chat Completions；
- **Anthropic Messages API**：DeepSeek 提供 `/anthropic` 端点，格式差异大（无 system role、工具用 `input_schema`），通吃 Claude 时需要单独适配层；
- **MCP**：工具协议标准化方向，agent 接外部工具大概率会碰到，可作为后续扩展点；
- **Beta 端点**：DeepSeek `/beta` 提供 strict 工具、Chat Prefix Completion，使用前确认是否值得依赖 Beta 特性；
- **参数别名差异**：`user`（OpenAI）vs `user_id`（DeepSeek）、`max_tokens` 语义差异等，provider 层做参数归一化。

## 7. 工程与安全

- **契约测试**：录制真实响应做 mock，离线测试协议解析、工具循环、流式聚合，避免每次测试都打 API；
- **可观测性**：每轮记录 token 消耗、耗时、finish_reason、模型名、重试次数；用 OpenTelemetry 做追踪；
- **密钥管理**：API key 走环境变量/密钥服务，绝不落日志；
- **日志脱敏**：请求/响应摘要化，剔除 key、敏感 content、reasoning_content；
- **安全**：工具权限最小化；对工具返回内容里的 prompt injection 保持警觉（恶意内容可能诱导模型调用危险工具）；`user` / `user_id` 传真实用户标识（内容安全与缓存隔离）；
- **成本监控**：按 usage 字段记账，prompt 缓存命中率是降本观察指标。

## 8. 落到本项目各层的分工建议

| 模块 | 负责内容 |
| --- | --- |
| `models/`（协议与数据结构） | Message / ToolCall / ChatRequest / ChatResponse / Usage，公共字段 + 可选扩展字段 |
| `provider.py` | 参数归一化、SSE 解析与聚合、错误映射、重试策略、usage 提取 |
| `agent.py` | 工具调用循环、max_iterations、上下文裁剪、会话状态、终止条件 |

优先实现顺序建议：

1. 消息结构与协议（已完成格式文档）；
2. 非流式调用 + 错误映射；
3. 工具调用闭环（含并行与异常回传）；
4. 流式聚合（content / tool_calls / reasoning_content / usage）；
5. 上下文裁剪与 token 统计；
6. 重试、限流、可观测性；
7. 契约测试与 mock。
