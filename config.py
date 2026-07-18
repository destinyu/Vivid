"""Vivid 配置模块：加载 .env，创建 API 客户端。"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = os.getenv("VIVID_MODEL", "deepseek-chat")
API_KEY = os.getenv("VIVID_API_KEY", "")
BASE_URL = os.getenv("VIVID_BASE_URL", "https://api.deepseek.com")

if not API_KEY:
    raise RuntimeError("未找到 VIVID_API_KEY。请检查 .env 文件。")

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
