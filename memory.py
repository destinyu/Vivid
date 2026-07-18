"""Vivid 记忆模块：长期记忆的加载、保存、提炼、注入。"""

import json
import os
from config import client, MODEL
from personality import PERSONALITY

MEMORY_FILE = "memory.json"
KEEP_RECENT = 10   # 上下文中保留最近 N 条
COMPRESS_OLD = 20  # 消息总数超过 (KEEP_RECENT + COMPRESS_OLD) 时压缩


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


def compress_context(messages: list, memory: dict) -> list:
    """如果消息超过阈值，提炼旧消息并裁剪上下文。返回裁剪后的 messages。"""
    MAX_MSG = KEEP_RECENT + COMPRESS_OLD
    if len(messages) <= MAX_MSG:
        return messages

    old_batch = messages[1:len(messages) - KEEP_RECENT]
    extracted = extract_memory(old_batch)
    if extracted:
        merge_memory(memory, extracted)
        messages[0] = {"role": "system", "content": build_system_prompt(memory)}
    return [messages[0]] + messages[-KEEP_RECENT:]


def finalize_memory(messages: list, memory: dict):
    """退出前强制提炼所有剩余消息。"""
    if len(messages) > 1:
        extracted = extract_memory(messages[1:])
        if extracted:
            merge_memory(memory, extracted)
    save_memory(memory)
