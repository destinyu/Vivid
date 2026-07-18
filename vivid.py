"""Vivid — 学习路上的契友"""

import json
from config import MODEL, client
from tools import TOOLS, handle_tool_call
from memory import (
    load_memory, compress_context, finalize_memory, build_system_prompt,
)


print(f"\nVivid 已就绪 · 模型：{MODEL}")
print(f"  上下文：最近 10 条 | 每 20 条旧消息压缩一次")

memory = load_memory()
if memory.get("topic"):
    print(f"  记忆中：正在学习 {memory['topic']}")
print()

messages = [{"role": "system", "content": build_system_prompt(memory)}]

while True:
    user_input = input("你: ").strip()
    if not user_input:
        continue
    if user_input.lower() in ("exit", "quit", "退出"):
        finalize_memory(messages, memory)
        print("再会。")
        break

    messages.append({"role": "user", "content": user_input})

    # ── 上下文压缩 ──
    messages = compress_context(messages, memory)

    # ── 调 API ──
    response = client.chat.completions.create(
        model=MODEL, messages=messages, tools=TOOLS,
    )
    assistant_msg = response.choices[0].message

    # ── 工具调用处理 ──
    if assistant_msg.tool_calls:
        if assistant_msg.content:
            print(f"Vivid: {assistant_msg.content}")
        messages.append(assistant_msg)

        for tool_call in assistant_msg.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            print(f"  🔧 调用工具：{name}({args})\n")
            result = handle_tool_call(name, args)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

        response2 = client.chat.completions.create(model=MODEL, messages=messages)
        reply = response2.choices[0].message.content
        messages.append({"role": "assistant", "content": reply})
    else:
        reply = assistant_msg.content
        messages.append({"role": "assistant", "content": reply})

    print(f"Vivid: {reply}\n")
