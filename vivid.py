"""Vivid — 学习路上的契友"""

import json
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = os.getenv("VIVID_MODEL", "deepseek-chat")
API_KEY = os.getenv("VIVID_API_KEY", "")
BASE_URL = os.getenv("VIVID_BASE_URL", "https://api.deepseek.com")

if not API_KEY:
    print("错误：未找到 VIVID_API_KEY。请检查 .env 文件。")
    exit(1)

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

with open("personality.md", encoding="utf-8") as f:
    PERSONALITY = f.read()

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "build_ladder",
            "description": "为学习主题建立5级学习阶梯。当用户表达想学某个主题的意愿时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "用户想学习的主题名称，如'Python编程'、'微观经济学'"
                    }
                },
                "required": ["topic"]
            }
        }
    }
]


def execute_build_ladder(topic: str) -> str:
    prompt = f"""为学习主题「{topic}」设计一个5级学习阶梯。从入门到精通。

返回格式（严格遵守）：
级别1：{topic}基础 — 核心概念（简短说明）
级别2：核心深入 — 核心概念（简短说明）
级别3：进阶专题 — 核心概念（简短说明）
级别4：实战应用 — 核心概念（简短说明）
级别5：精通 — 核心概念（简短说明）

每级一行。不要编号之外的文字。"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


print(f"\nVivid 已就绪 · 模型：{MODEL}\n")
messages = [{"role": "system", "content": PERSONALITY}]

while True:
    user_input = input("你: ").strip()
    if not user_input:
        continue
    if user_input.lower() in ("exit", "quit", "退出"):
        print("再会。")
        break

    messages.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
    )

    assistant_msg = response.choices[0].message

    if assistant_msg.tool_calls:
        if assistant_msg.content:
            print(f"Vivid: {assistant_msg.content}")

        messages.append(assistant_msg)

        for tool_call in assistant_msg.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            print(f"  🔧 调用工具：{name}({args})\n")

            if name == "build_ladder":
                result = execute_build_ladder(args["topic"])
            else:
                result = f"未知工具：{name}"

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

        response2 = client.chat.completions.create(
            model=MODEL,
            messages=messages,
        )
        reply = response2.choices[0].message.content
        messages.append({"role": "assistant", "content": reply})

    else:
        reply = assistant_msg.content
        messages.append({"role": "assistant", "content": reply})

    print(f"Vivid: {reply}\n")
