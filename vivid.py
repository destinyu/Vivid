"""Vivid — 学习路上的契友"""

import os
from dotenv import load_dotenv
from openai import OpenAI

# ── 1. 加载配置 ──
load_dotenv()

MODEL = os.getenv("VIVID_MODEL", "deepseek-chat")
API_KEY = os.getenv("VIVID_API_KEY", "")
BASE_URL = os.getenv("VIVID_BASE_URL", "https://api.deepseek.com")

if not API_KEY:
    print("错误：未找到 VIVID_API_KEY。请检查 .env 文件。")
    exit(1)

# ── 2. 创建 API 客户端 ──
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# ── 3. 加载人格 ──
with open("personality.md", encoding="utf-8") as f:
    PERSONALITY = f.read()

# ── 4. 对话循环 ──
print(f"\nVivid 已就绪 · 模型：{MODEL}\n")

while True:
    user_input = input("你: ").strip()
    if not user_input:
        continue
    if user_input.lower() in ("exit", "quit", "退出"):
        print("再会。")
        break

    # 调 API
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": PERSONALITY},
            {"role": "user", "content": user_input},
        ],
    )

    reply = response.choices[0].message.content
    print(f"\nVivid: {reply}\n")
