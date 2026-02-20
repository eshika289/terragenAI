import os

import requests

from .config import load_config

DEFAULT_API_URL = "http://your-rag-service/chat"


def get_api_url() -> str:
    env_api_url = os.getenv("TERRAGENAI_API_URL")
    if env_api_url:
        return env_api_url

    config_api_url = load_config().get("api_url")
    if config_api_url:
        return config_api_url

    return DEFAULT_API_URL


def send_message(history: list[dict]) -> str:
    api_url = get_api_url()

    if api_url == DEFAULT_API_URL:
        return "Test response: run with --configure (or set TERRAGENAI_API_URL) to call your backend."

    response = requests.post(api_url, json={"messages": history}, timeout=30)
    response.raise_for_status()
    data = response.json()
    return data.get("response", str(data))
