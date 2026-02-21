import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List

import hcl2
import requests

from ...models.module_registry import ModuleRegistry
from ...paths import get_config_dir

# TODO: Refactor


class ModuleRegistryService:
    def __init__(self):
        self.registry = ModuleRegistry()
        print(self.registry.TF_ORG)

        base_dir = os.path.join(str(get_config_dir()), self.registry.TF_ORG)
        os.makedirs(base_dir, exist_ok=True)
        self.repo_dir = os.path.join(base_dir, "registry-repos")
        self.catalog_dir = os.path.join(base_dir, "catalog")
        self.catalog_path = os.path.join(self.catalog_dir, "modules.json")

    # ------------------------------
    # Module Registry helpers
    # ------------------------------
    def _http_get(self, url: str) -> Dict:
        resp = requests.get(url, headers=self.registry.TF_HEADERS)
        resp.raise_for_status()
        return resp.json()

    def _list_registry_modules(
        self,
    ) -> List[Dict]:
        url = self.registry.TF_REGISTRY_MODULES_URL
        modules = []

        while url:
            data = self._http_get(url)
            modules.extend(data.get("data", []))
            url = data.get("links", {}).get("next")

        return modules

    # ------------------------------
    # Git helpers
    # ------------------------------
    def _git_clone_repo(self, repo_url: str):

        if self.registry.GIT_CLONE_TOKEN:
            repo_url = repo_url.replace(
                "https://", f"https://{self.registry.GIT_CLONE_TOKEN}@"
            )
            repo_url = repo_url.replace(
                "http://", f"http://{self.registry.GIT_CLONE_TOKEN}@"
            )
        subprocess.run(["git", "clone", "--quiet", repo_url, self.repo_dir], check=True)

    def _git_checkout_tag(self, tag: str):
        subprocess.run(
            ["git", "checkout", "--quiet", tag], cwd=self.repo_dir, check=True
        )

    # ------------------------------
    # Terraform parsing
    # ------------------------------
    def _parse_tf_variables(self) -> List[Dict]:
        variables = []

        for root, _, files in os.walk(self.repo_dir):
            for file in files:
                if not file.endswith(".tf"):
                    continue

                path = os.path.join(root, file)
                try:
                    with open(path, "r") as f:
                        parsed = hcl2.load(f)
                except Exception:
                    continue

                for block in parsed.get("variable", []):
                    for name, attrs in block.items():
                        variables.append(
                            {
                                "name": name,
                                "type": attrs.get("type"),
                                "description": attrs.get("description"),
                                "default": attrs.get("default"),
                                "required": "default" not in attrs,
                            }
                        )

        # Deduplicate by name
        unique = {v["name"]: v for v in variables}
        return list(unique.values())

    def _list_repo_files(self) -> List[str]:
        files = []
        for root, _, filenames in os.walk(self.repo_dir):
            for f in filenames:
                rel = os.path.relpath(os.path.join(root, f), self.repo_dir)
                files.append(rel)
        return files

    # ------------------------------
    # Main catalog builder
    # ------------------------------
    def build_catalog(self):
        os.makedirs(self.catalog_dir, exist_ok=True)
        catalog = {}

        print(f"🔍 Fetching Terraform modules for org: {self.registry.TF_ORG}")
        modules = self._list_registry_modules()

        for mod in modules:
            attrs = mod["attributes"]

            name = attrs["name"]
            namespace = attrs["namespace"]
            provider = attrs["provider"]
            vcs = attrs.get("vcs-repo")
            versions = attrs.get("version-statuses", [])

            if not vcs:
                print(f"⚠ Skipping {name}: no VCS repo")
                continue

            repo_url = vcs["repository-http-url"]

            print(f"\n📦 Module: {namespace}/{name}/{provider}")
            print(f"   Repo: {repo_url}")

            catalog.setdefault(repo_url, {})

            try:
                self._git_clone_repo(repo_url)
            except Exception as e:
                print(f"❌ Failed to clone {repo_url}: {e}")
                continue

            for v in versions:
                tag = v.get("version")
                if not tag.startswith("v"):
                    tag = f"v{tag}"

                try:
                    self._git_checkout_tag(tag)
                except Exception:
                    print(f"⚠ Tag {tag} not found, skipping")
                    continue

                print(f"   → Processing version {tag}")

                variables = self._parse_tf_variables()
                files = self._list_repo_files()

                catalog[repo_url][tag] = {
                    "module_name": name,
                    "namespace": namespace,
                    "provider": provider,
                    "source": f"{self.registry.TF_REGISTRY_DOMAIN}/{namespace}/{name}/{provider}",
                    "variables": variables,
                    "files": files,
                    "vcs_available": True,
                    "vcs_link": f"{repo_url}/tree/{tag}",
                }

            shutil.rmtree(self.repo_dir)

        with open(self.catalog_path, "w") as f:
            json.dump(catalog, f, indent=2)

        print(f"\n✅ Catalog written to {self.catalog_path}")
        print(f"📊 Total repos indexed: {len(catalog)}")

    # ------------------------------
    # Validate Catalog Exists
    # ------------------------------
    def validate_catalog(self):
        p = Path(self.catalog_path)
        return p.is_file() and p.stat().st_size > 0
