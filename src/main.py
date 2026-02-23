import argparse
import sys

from rich import print

from . import __version__
from .client import send_message
from .config import get_config_file, load_config, save_config
from .services.registry.terraform_registry import ModuleRegistryService
from .services.vector_store.faiss_store import FaissService
from .services.session.session import SessionService

def chat() -> None:
    session_service = SessionService()
    registry_service = get_registry_service()
    if not registry_service.validate_catalog():
        print(
            "[bold red]Registry module catalog not found. Run terragenai --sync first.[/bold red]"
        )
        return

    history = session_service.load_session()

    catalog = registry_service.pull_catalog()
    vector_store = FaissService(catalog)
    vector_store.create_index()
    print("[bold green]TerragenAI Chat started. Type 'exit' to quit.[/bold green]")

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        session_service.add_message(history, "user", user_input)
        print("[yellow]Thinking...[/yellow]")
        response = send_message(user_input, history, vector_store)
        print(f"\n[bold blue]Assistant:[/bold blue] {response}")
        session_service.add_message(history, "assistant", str(response))
    
    session_service.clear_session()


def configure() -> None:
    current = load_config()
    tf_org = input(
        f"Enter TF_ORG [{current.get('TF_ORG', '')}]: "
    ).strip() or current.get("TF_ORG", "")
    tf_registry_domain = (
        input(
            "Enter TF_REGISTRY_DOMAIN "
            f"[{current.get('TF_REGISTRY_DOMAIN') or 'app.terraform.io'}]: "
        ).strip()
        or current.get("TF_REGISTRY_DOMAIN")
        or "app.terraform.io"
    )
    tf_api_token = input(
        f"Enter TF_API_TOKEN [{current.get('TF_API_TOKEN', '')}]: "
    ).strip() or current.get("TF_API_TOKEN", "")
    git_clone_token = input(
        f"Enter GIT_CLONE_TOKEN [{current.get('GIT_CLONE_TOKEN', '')}]: "
    ).strip() or current.get("GIT_CLONE_TOKEN", "")
    openai_api_key = input(
        f"Enter OPENAI_API_KEY [{current.get('OPENAI_API_KEY', '')}]: "
    ).strip() or current.get("OPENAI_API_KEY", "")
    config = {
        "TF_ORG": tf_org,
        "TF_REGISTRY_DOMAIN": tf_registry_domain,
        "TF_API_TOKEN": tf_api_token,
        "GIT_CLONE_TOKEN": git_clone_token,
        "OPENAI_API_KEY": openai_api_key,
    }
    save_config(config)
    print("[bold green]Saved configuration.[/bold green]")
    print(f"TF_ORG: {tf_org or '(not set)'}")
    print(f"TF_REGISTRY_DOMAIN: {tf_registry_domain}")
    print(f"TF_API_TOKEN: {'(set)' if tf_api_token else '(not set)'}")
    print(f"GIT_CLONE_TOKEN: {'(set)' if git_clone_token else '(not set)'}")
    print(f"OPENAI_API_KEY: {'(set)' if openai_api_key else '(not set)'}")
    print(f"Config file: {get_config_file()}")


registry_service = None


def get_registry_service():
    global registry_service
    if registry_service is None:
        registry_service = ModuleRegistryService()
    return registry_service


def sync_registry_modules():
    registry_service = get_registry_service()
    registry_service.build_catalog()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="terragenai",
        description="Simple Terragen AI chat CLI.",
    )
    parser.add_argument(
        "-v", "--version", action="store_true", help="Show version and exit."
    )
    parser.add_argument(
        "--configure", action="store_true", help="Configure CLI settings."
    )
    parser.add_argument(
        "--sync",
        "--sync-registry-modules",
        dest="sync_registry_modules",
        action="store_true",
        help="Sync the latest modules from your Terraform Cloud/Enterprise private registry.",
    )
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

    if args.sync_registry_modules:
        sync_registry_modules()
        return

    chat()


if __name__ == "__main__":
    run()
