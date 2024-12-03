import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel


class Settings(BaseModel):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "ChatExaminer"
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # 文件路径
    ROOT_DIR: Path = Path(__file__).parent.parent.parent.parent
    DATA_DIR: Path = ROOT_DIR / "data"
    QUESTIONS_FILE: Path = DATA_DIR / "exam_questions.json"


# 确保 .env 文件路径正确
env_path = Path(__file__).parent.parent.parent.parent / ".env"

print(f"Current working directory: {os.getcwd()}")
print(f"Looking for .env at: {env_path}")

if not env_path.exists():
    raise FileNotFoundError(f".env file not found at {env_path}")

load_dotenv(env_path)
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

client = OpenAI(api_key=api_key)
settings = Settings()

# 确保数据目录存在
settings.DATA_DIR.mkdir(exist_ok=True)
