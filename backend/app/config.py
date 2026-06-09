"""
全局配置，从环境变量读取。
运行前复制 .env.example 为 .env 并填写实际值。
"""
import os
from dotenv import load_dotenv

load_dotenv()

# DeepSeek API
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 服务配置
APP_TITLE: str = "校园安全导览系统 API"
APP_VERSION: str = "0.1.0"
CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

# ArcPy / GIS 配置（mdb 就绪后填写）
MDB_PATH: str = os.getenv("MDB_PATH", "")
NETWORK_DATASET: str = os.getenv("NETWORK_DATASET", "")
