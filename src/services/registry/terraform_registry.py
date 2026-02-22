import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import hcl2
import requests

from ...models.module_registry import ModuleRegistry
from ...paths import get_config_dir


@dataclass(frozen=True)
class TerraformVariableMetadata:
    name: str
    type: Any
    description: Any
    default: Any
    required: bool


@dataclass(frozen=True)
class CatalogEntry:
    module_name: str
    namespace: str
    provider: str
    source: str
    variables: List[Dict[str, Any]]
    files: List[str]
    vcs_available: bool
    vcs_link: str


class ModuleRegistryService:
    def __init__(
        self,
        registry: Optional[ModuleRegistry] = None,
        config_dir: Optional[Path] = None,
        session: Optional[requests.Session] = None,
    ):
        self.registry = registry or ModuleRegistry()
        self.session = session or requests.Session()

        config_root = Path(config_dir) if config_dir else Path(get_config_dir())
        base_dir = config_root / self.registry.TF_ORG
        base_dir.mkdir(parents=True, exist_ok=True)

        self.repo_dir = str(base_dir / "registry-repos")
        self.catalog_dir = str(base_dir / "catalog")
        self.catalog_path = str(Path(self.catalog_dir) / "modules.json")

        Path(self.repo_dir).mkdir(parents=True, exist_ok=True)

    # ------------------------------
    # Module Registry helpers
    # ------------------------------
    def _http_get(self, url: str) -> Dict[str, Any]:
        last_error: Optional[requests.RequestException] = None
        for _ in range(3):
            try:
                resp = self.session.get(
                    url, headers=self.registry.TF_HEADERS, timeout=30
                )
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as exc:
                last_error = exc
        if last_error:
            raise last_error
        raise RuntimeError("Request failed without an exception")

    def _list_registry_modules(self) -> List[Dict[str, Any]]:
        url = self.registry.TF_REGISTRY_MODULES_URL
        modules: List[Dict[str, Any]] = []

        while url:
            data = self._http_get(url)
            modules.extend(data.get("data", []))
            url = data.get("links", {}).get("next")

        return modules

    # ------------------------------
    # Git helpers
    # ------------------------------
    def _clone_url(self, repo_url: str) -> str:
        if self.registry.GIT_CLONE_TOKEN:
            repo_url = repo_url.replace(
                "https://", f"https://{self.registry.GIT_CLONE_TOKEN}@"
            )
            repo_url = repo_url.replace(
                "http://", f"http://{self.registry.GIT_CLONE_TOKEN}@"
            )
        return repo_url

    def _git_clone_repo(self, repo_url: str, clone_dir: Path):
        subprocess.run(
            ["git", "clone", "--quiet", self._clone_url(repo_url), str(clone_dir)],
            check=True,
        )

    def _git_checkout_tag(self, repo_dir: Path, tag: str):
        subprocess.run(
            ["git", "checkout", "--quiet", tag], cwd=str(repo_dir), check=True
        )

    # ------------------------------
    # Terraform parsing
    # ------------------------------
    def _parse_tf_variables(self, repo_dir: Path) -> List[Dict[str, Any]]:
        variables: List[TerraformVariableMetadata] = []

        for root, _, files in os.walk(repo_dir):
            for file in files:
                if not file.endswith(".tf"):
                    continue

                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        parsed = hcl2.load(f)
                except Exception:
                    continue

                for block in parsed.get("variable", []):
                    for name, attrs in block.items():
                        variables.append(
                            TerraformVariableMetadata(
                                name=name,
                                type=attrs.get("type"),
                                description=attrs.get("description"),
                                default=attrs.get("default"),
                                required="default" not in attrs,
                            )
                        )

        # Deduplicate by name
        unique = {v.name: v for v in variables}
        return [asdict(variable) for variable in unique.values()]

    def _list_repo_files(self, repo_dir: Path) -> List[str]:
        files: List[str] = []
        for root, dirnames, filenames in os.walk(repo_dir):
            if ".git" in dirnames:
                dirnames.remove(".git")
            for filename in filenames:
                rel = os.path.relpath(os.path.join(root, filename), repo_dir)
                files.append(rel)
        return files

    def _normalize_tag(self, version: Any) -> Optional[str]:
        if not version:
            return None

        tag = str(version)
        if not tag.startswith("v"):
            tag = f"v{tag}"
        return tag

    def _build_catalog_entry(
        self,
        module_name: str,
        namespace: str,
        provider: str,
        repo_url: str,
        tag: str,
        variables: List[Dict[str, Any]],
        files: List[str],
    ) -> Dict[str, Any]:
        return asdict(
            CatalogEntry(
                module_name=module_name,
                namespace=namespace,
                provider=provider,
                source=f"{self.registry.TF_REGISTRY_DOMAIN}/{namespace}/{module_name}/{provider}",
                variables=variables,
                files=files,
                vcs_available=True,
                vcs_link=f"{repo_url}/tree/{tag}",
            )
        )

    def _write_catalog(self, catalog: Dict[str, Any]) -> None:
        catalog_dir_path = Path(self.catalog_dir)
        catalog_dir_path.mkdir(parents=True, exist_ok=True)

        tmp_path: Optional[Path] = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", dir=catalog_dir_path, delete=False, encoding="utf-8"
            ) as tmp:
                json.dump(catalog, tmp, indent=2)
                tmp_path = Path(tmp.name)
            os.replace(tmp_path, self.catalog_path)
        finally:
            if tmp_path and tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    # ------------------------------
    # Main catalog builder
    # ------------------------------
    def build_catalog(self):
        catalog: Dict[str, Dict[str, Dict[str, Any]]] = {}

        print(f"Fetching Terraform modules for org: {self.registry.TF_ORG}")
        modules = self._list_registry_modules()
        print(f"Found {len(modules)} module(s)")

        for mod in modules:
            attrs = mod.get("attributes", {})
            name = attrs.get("name")
            namespace = attrs.get("namespace")
            provider = attrs.get("provider")
            vcs = attrs.get("vcs-repo")
            versions = attrs.get("version-statuses", [])

            if not name or not namespace or not provider:
                print(
                    f"WARNING: Skipping module with incomplete metadata: {attrs}",
                    file=sys.stderr,
                )
                continue

            if not vcs:
                print(f"WARNING: Skipping {name}: no VCS repo", file=sys.stderr)
                continue

            repo_url = vcs.get("repository-http-url")
            if not repo_url:
                print(
                    f"WARNING: Skipping {name}: missing repository-http-url",
                    file=sys.stderr,
                )
                continue

            print(f"Processing {namespace}/{name}/{provider}")
            catalog.setdefault(repo_url, {})

            repo_tmp_dir = Path(tempfile.mkdtemp(dir=self.repo_dir))
            clone_dir = repo_tmp_dir / "repo"

            try:
                self._git_clone_repo(repo_url, clone_dir)
            except subprocess.CalledProcessError as exc:
                print(f"ERROR: Failed to clone {repo_url}: {exc}", file=sys.stderr)
                shutil.rmtree(repo_tmp_dir, ignore_errors=True)
                continue

            try:
                for version in versions:
                    tag = self._normalize_tag(version.get("version"))
                    if not tag:
                        print(
                            f"WARNING: Skipping invalid version for {name}: {version}",
                            file=sys.stderr,
                        )
                        continue

                    try:
                        self._git_checkout_tag(clone_dir, tag)
                    except subprocess.CalledProcessError:
                        print(
                            f"WARNING: Tag {tag} not found for {repo_url}, skipping",
                            file=sys.stderr,
                        )
                        continue

                    variables = self._parse_tf_variables(clone_dir)
                    files = self._list_repo_files(clone_dir)
                    catalog[repo_url][tag] = self._build_catalog_entry(
                        module_name=name,
                        namespace=namespace,
                        provider=provider,
                        repo_url=repo_url,
                        tag=tag,
                        variables=variables,
                        files=files,
                    )
                    print(f"  Indexed {tag}")
            finally:
                shutil.rmtree(repo_tmp_dir, ignore_errors=True)

        self._write_catalog(catalog)

        print(f"\nDone. {len(catalog)} repo(s) indexed.")
        print(f"Catalog written to {self.catalog_path}")

    # ------------------------------
    # Validate Catalog Exists
    # ------------------------------
    def validate_catalog(self):
        p = Path(self.catalog_path)
        return p.is_file() and p.stat().st_size > 0
