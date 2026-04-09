import os
from dataclasses import dataclass

@dataclass
class AppConfig:
    debug: bool = True
    # placeholders for later
    pinecone_api_key: str = os.getenv("PINECONE_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    # model names etc. will go here later

config = AppConfig()
