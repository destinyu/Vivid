"""Vivid — 学习路上的契友"""

import json
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ── 配置 ──
MODEL = os.getenv("VIVID_MODEL", "deepseek-chat")
API_KEY = os.getenv("VIVID_API_KEY", "")
BASE_URL = os.getenv("VIVID_BASE_URL", "https://api.deepseek.com")

if not API_KEY:
    print("错误：未找到 VIVID_API_KEY。请检查 .env 文件。")
    exit(1)

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

with open("personality.md", encoding="utf-8") as f:
    PERSONALITY = f.read()

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

# ── 上下文与记忆 ──
MEMORY_FILE = "memory.json"
KEEP_RECENT = 10   # 上下文中保留最近 N 条消息
COMPRESS_OLD = 20  # 超过 (KEEP_RECENT + COMPRESS_OLD) 条时，压缩旧消息


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


def load_memory() -> dict:
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"topic": "", "progress": "", "weak_points": [],
            "preferences": [], "key_facts": []}


def save_memory(memory: dict):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)


def extract_memory(messages_batch: list) -> str:
    """从旧消息中提炼关键信息，返回 LLM 生成的 JSON 字符串。"""
    transcript = ""
    for m in messages_batch:
        role = m["role"] if isinstance(m, dict) else getattr(m, "role", "?")
        content = m["content"] if isinstance(m, dict) else getattr(m, "content", "") or ""
        if content and role in ("user", "assistant"):
            transcript += f"[{role}] {content[:200]}\n"

    if not transcript.strip():
        return ""

    prompt = f"""从以下对话片段中提取学习相关信息。只提取、不编造。

{transcript}

返回 JSON 格式（只返回 JSON，不要其他文字）：
{{
    "topic": "正在学习的主题（没有就空字符串）",
    "progress": "学习进度描述（没有就空字符串）",
    "weak_points": ["薄弱点1"],
    "preferences": ["学习偏好1"],
    "key_facts": ["值得记住的事实1"]
}}"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception:
        return ""


def merge_memory(memory: dict, extracted: str):
    """将 LLM 提炼结果合并到记忆中。"""
    try:
        if extracted.startswith("```"):
            extracted = extracted.split("\n", 1)[1]
            if extracted.endswith("```"):
                extracted = extracted.rsplit("\n", 1)[0]
        new_info = json.loads(extracted)
    except Exception:
        return

    if new_info.get("topic") and new_info["topic"] not in memory["topic"]:
        memory["topic"] = (memory["topic"] + "; " + new_info["topic"]
                           if memory["topic"] else new_info["topic"])
    if new_info.get("progress"):
        memory["progress"] = new_info["progress"]
    for item in new_info.get("weak_points", []):
        if item not in memory["weak_points"]:
            memory["weak_points"].append(item)
    for item in new_info.get("preferences", []):
        if item not in memory["preferences"]:
            memory["preferences"].append(item)
    for item in new_info.get("key_facts", []):
        if item not in memory["key_facts"]:
            memory["key_facts"].append(item)


def build_system_prompt(memory: dict) -> str:
    """将记忆注入 system prompt。"""
    parts = [PERSONALITY]
    if any(memory.values()):
        parts.append("\n\n## 用户学习状态（从之前对话中提炼）")
        if memory.get("topic"):
            parts.append(f"- 正在学习：{memory['topic']}")
        if memory.get("progress"):
            parts.append(f"- 当前进度：{memory['progress']}")
        if memory.get("weak_points"):
            parts.append(f"- 薄弱点：{'、'.join(memory['weak_points'])}")
        if memory.get("preferences"):
            parts.append(f"- 学习偏好：{'、'.join(memory['preferences'])}")
        if memory.get("key_facts"):
            parts.append(f"- 关键信息：{'、'.join(memory['key_facts'])}")
        parts.append("")
    return "\n".join(parts)


# ── 启动 ──
MAX_MSG = KEEP_RECENT + COMPRESS_OLD  # 消息总数超过此值触发压缩

memory = load_memory()
print(f"\nVivid 已就绪 · 模型：{MODEL}")
print(f"  上下文：最近 {KEEP_RECENT} 条 | 每 {COMPRESS_OLD} 条旧消息压缩一次")
if memory.get("topic"):
    print(f"  记忆中：正在学习 {memory['topic']}")
print()

messages = [{"role": "system", "content": build_system_prompt(memory)}]

while True:
    user_input = input("你: ").strip()
    if not user_input:
        continue
    if user_input.lower() in ("exit", "quit", "退出"):
        # 退出前强制提炼剩余消息（避免短对话丢失）
        if len(messages) > 1:
            old_batch = messages[1:]  # system 之后的所有消息
            extracted = extract_memory(old_batch)
            if extracted:
                merge_memory(memory, extracted)
        save_memory(memory)
        print("再会。")
        break

    messages.append({"role": "user", "content": user_input})

    # ── 压缩：消息超过阈值 → 提炼旧消息 → 裁剪 ──
    if len(messages) > MAX_MSG:
        # 提炼 [1] 到 [len-KEEP_RECENT] 的旧消息（约20条）
        old_end = len(messages) - KEEP_RECENT
        old_batch = messages[1:old_end]
        extracted = extract_memory(old_batch)
        if extracted:
            merge_memory(memory, extracted)
            messages[0] = {"role": "system", "content": build_system_prompt(memory)}
        # 保留 system + 最近 KEEP_RECENT 条
        messages = [messages[0]] + messages[-KEEP_RECENT:]

    # ── 调 API ──
    response = client.chat.completions.create(
        model=MODEL, messages=messages, tools=TOOLS,
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
                "role": "tool", "tool_call_id": tool_call.id, "content": result,
            })

        response2 = client.chat.completions.create(model=MODEL, messages=messages)
        reply = response2.choices[0].message.content
        messages.append({"role": "assistant", "content": reply})
    else:
        reply = assistant_msg.content
        messages.append({"role": "assistant", "content": reply})

    print(f"Vivid: {reply}\n")
