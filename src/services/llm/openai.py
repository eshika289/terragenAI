import os

from openai import OpenAI
from rich import print

from ...config import load_config
from .base_llm import LLMService


class OpenAIService(LLMService):

    def __init__(self):
        config = load_config()
        OPENAI_API_KEY = config.get("OPENAI_API_KEY", "").strip()
        if not OPENAI_API_KEY:
            print("[bold red]Error: No OpenAI API key found[/bold red]")
            exit(1)
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.dry_run = os.getenv("DRY_RUN", "").lower() == "true"

    def create_embedding(self, text: str) -> list[float]:
        if self.dry_run:
            print("DRY_RUN==true, no LLM calls")
            return None
        return (
            self.client.embeddings.create(model="text-embedding-3-small", input=text)
            .data[0]
            .embedding
        )

    def generate(self, messages: list[dict]):
        if self.dry_run:
            print("DRY_RUN==true, no LLM calls")
            return [{"DRY_RUN==true, no LLM calls"}]
        response = self.client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            messages=messages,
            temperature=0,
        )
        reply = response.choices[0].message.content
        return reply
