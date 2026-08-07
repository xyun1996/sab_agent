```json
{
  "id": "bfcddb79-2db0-4292-bde2-f029def46ac4",
  "object": "chat.completion",
  "created": 1785981993,
  "model": "deepseek-v4-flash",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hi! \ud83d\udc4b How can I help you today?",
        "reasoning_content": "The user just said \"hi\". This is a simple greeting. I should respond in a friendly and helpful manner. Since this is the start of the conversation, I'll greet them back and ask how I can help. Keep it warm and open-ended."
      },
      "logprobs": null,
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 90,
    "completion_tokens": 63,
    "total_tokens": 153,
    "prompt_tokens_details": {
      "cached_tokens": 0
    },
    "completion_tokens_details": {
      "reasoning_tokens": 51
    },
    "prompt_cache_hit_tokens": 0,
    "prompt_cache_miss_tokens": 90
  },
  "system_fingerprint": "fp_a18b46594c_prod0820_fp8_kvcache_20260402"
}
```

## 顶层

**id** —— **bfcddb79...** : 本次完成的唯一ID(UUID)。用于排查日志、对账; 多轮对话不用回传。
**object** —— **chat.completion** : 对象类型标记，固定值。流式为**chat.completion.chunk**。
**created** —— **1785981993** : Unix时间戳(秒)
**model** —— **deepseek-v4-flash** : 实际处理请求的模型。

### choice[0]

**index** —— 0 : 第几个候选结果。基本返回一个。
**message** —— 消息对象:

- **role** —— **assistant** : 消息角色。回传历史时这条消息要原样塞回messages。
- **content** —— **Hi...** : 最终回答文本。注意纯工具调用这里是null。
- **reasoning_content** —— "The user..." : 思考过程全文 (DS thinking特有)。模型先思考后回答，这段是"思维链":
  - 不计入content，但计入计费
  - 不要回传进下一轮历史
  - 日志里建议脱敏，可能包含敏感信息。

**logprobs** —— **null** : 对数概率。token级概率数据。
**finish_reason** —— **stop** : 停止原因，agent分支逻辑的核心；

| 值                           | 含义                                     |
| :--------------------------- | :--------------------------------------- |
| stop                         | 正常结束(本次)                           |
| length                       | 达到max_tokens，内容可能被截断，需要处理 |
| tool_calls                   | 模型请求工具调用，走工具循环             |
| content_filter               | 内容被过滤                               |
| insufficient_system_resource | 服务端资源不足终端(DS特有)               |

### usage(计费与统计)
**prompt_tokens** —— **90** : 输入token数。
**completion_tokens** —— **63** : 输出token数(含思考)。
**total_tokens** —— **153** : 90 + 63，请求总消耗，按这个记账。
**prompt_tokens_details.cached_tokens** —— **0** : 命中上下文缓存的输入token。
**completion_tokens_details.reasoning_tokens** —— **51** : 63个输出中有51个是思考过程。
**prompt_cache_hit_tokens** —— **0** : 缓存命中(DS风格字段，与cached_tokens同一件事两种写法)
**prompt_cache_miss_tokens** —— **90** : 未命中缓存的输入token。命中+未命中=prompt_tokens。

### system_fingerprint
**fp_a18b46594c_prod0820_fp8_kvcache_20260402** : 后端配置指纹。含义"本次请求泡在那套推理配置上" —— **fp8_kvcache** 表示KV缓存/量化相关部署，日期段是部署版本。