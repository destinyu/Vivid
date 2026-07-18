"""Vivid 工具模块：工具定义 + 工具实现。"""

import json
from config import client, MODEL

# ── 工具定义 ──
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
    """调用 API 生成 5 级学习阶梯。"""
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


def handle_tool_call(name: str, args: dict) -> str:
    """执行工具调用。返回工具执行结果。"""
    if name == "build_ladder":
        return execute_build_ladder(args["topic"])
    return f"未知工具：{name}"
