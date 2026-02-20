import argparse
import sys
from rich import print

from . import __version__
from .client import send_message
from .config import get_config_file, load_config, save_config
from .memory import add_message, load_history

def chat() -> None:
    history = load_history()
    print("[bold green]LLM CLI started. Type 'exit' to quit.[/bold green]")

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        add_message(history, "user", user_input)
        print("[yellow]Thinking...[/yellow]")
        response = send_message(history)
        print(f"\n[bold blue]Assistant:[/bold blue] {response}")
        add_message(history, "assistant", response)


def configure() -> None:
    current = load_config()
    existing_api_url = current.get("api_url", "")
    prompt = f"Enter API URL [{existing_api_url or 'http://localhost:8000/chat'}]: "
    api_url = input(prompt).strip() or existing_api_url or "http://localhost:8000/chat"
    config = {"api_url": api_url}
    save_config(config)
    print("[bold green]Saved configuration.[/bold green]")
    print(f"API URL: {api_url}")
    print(f"Config file: {get_config_file()}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="terragenai",
        description="Simple Terragen AI chat CLI.",
    )
    parser.add_argument("-v", "--version", action="store_true", help="Show version and exit.")
    parser.add_argument("--configure", action="store_true", help="Configure CLI settings.")
    return parser


def run() -> None:
    if len(sys.argv) == 1:
        chat()
        return
    args = build_parser().parse_args()

    if args.version:
        print(__version__)
        return

    if args.configure:
        configure()
        return

    chat()


if __name__ == "__main__":
    run()
