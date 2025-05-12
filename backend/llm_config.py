from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

class LLMConfig:
    _instance = None
    _llm = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if LLMConfig._llm is None:
            LLMConfig._llm = ChatOpenAI(
                model="gpt-4.1-nano",
                api_key=os.getenv('OPENAI_API_KEY')
            )

    @property
    def llm(self):
        return self._llm

# Create a global instance
llm_config = LLMConfig.get_instance()

# Export the llm instance for easy access
llm = llm_config.llm 