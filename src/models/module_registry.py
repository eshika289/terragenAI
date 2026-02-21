from ..config import load_config


class ModuleRegistry:

    def __init__(self):

        config = load_config()

        # Pulled directly from configuration
        self.TF_ORG = config.get("TF_ORG", "").strip()
        self.TF_REGISTRY_DOMAIN = config.get(
            "TF_REGISTRY_DOMAIN", "app.terraform.io"
        ).strip()
        self.TF_API_TOKEN = config.get("TF_API_TOKEN", "").strip()
        self.GIT_CLONE_TOKEN = config.get("GIT_CLONE_TOKEN", "").strip()

        # Generated from configuration
        self.IS_TFE = self.TF_REGISTRY_DOMAIN != "app.terraform.io"
        self.TF_BASE_URL = f"https://{self.TF_REGISTRY_DOMAIN}/api/v2"
        self.TF_REGISTRY_MODULES_URL = (
            f"{self.TF_BASE_URL}/organizations/{self.TF_ORG}/registry-modules"
        )
        self.TF_HEADERS = {
            "Authorization": f"Bearer {self.TF_API_TOKEN}",
            "Content-Type": "application/vnd.api+json",
        }

        self._validate()

    def _validate(self) -> None:
        # TODO
        missing = []
        if not self.TF_ORG:
            missing.append("TF_ORG")
        if not self.TF_API_TOKEN:
            missing.append("TF_API_TOKEN")
        if missing:
            raise ValueError(
                f"Missing required config: {', '.join(missing)}. Run `terragenai --configure`."
            )
