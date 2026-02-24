# terragenAI

**Problem Statement**: Large language models (LLMs) can generate Terraform configuration blocks quickly, but lack awareness of an organization's private modules, which are often required for consistency, security, and compliance.  As a result, LLM-generated suggestions are often incompatible with an organization's internal standards and cannot be used directly. 

**Solution**: A command line interface (CLI) tool that provides a conversational AI agent that is aware of an organization's Terraform Cloud or Enterprise private modules. It uses **retrieval-augmented generation (RAG) via a vector database (FAISS)** to ground responses in the organization's private module registry. Additionally, it **provides citations** of the specific modules and versions used and **avoids hallucinations** by indicating when there is no available module that supports the user's request. Via this tool, engineering teams can leverage AI-assisted code generation while maintaining adherence to organizational policies.


## Features & How It Works

**Terraform Cloud/Enterprise Private Module Registry Parser** (`terragenai --sync`)
1. Fetches all modules from the TFC/TFE private registry API with pagination
2. Clones each module repo via Git — VCS-agnostic, compatible with GitHub, GitLab, and Bitbucket
3. Parses all `.tf` files using `python-hcl2` to extract variable metadata (name, type, default, required)
4. Embeds each module using a configurable embedding model and builds a local FAISS `IndexFlatL2` index
5. Persists the module catalog (`modules.json`) and FAISS index to disk
6. To update local cache, run `terragenai --sync`

**Conversational RAG-based Terraform AI Agent** (`terragenai`)
1. User prompt is embedded and similarity-searched against the FAISS index
2. Top-k most relevant modules are injected into the LLM system prompt as structured inventory
3. The configured LLM generates HCL constrained to the provided modules only
4. Every response includes a citation comment with the VCS link of each module used
5. If no relevant module exists for a request, the model is explicitly instructed to say so rather than hallucinating responses
6. Chat history is persisted per session, capped at 10 messages sent to the LLM


## Engineering Highlights

**Abstract service layer** -- LLMService and VectorStoreService are ABC classes. Alternative providers can be swapped in without touching the CLI or client code. Follows the strategy pattern to avoid tightly coupling LLM and vector store implementations with business logic.

**Session management** -- Each run creates a UUID-backed session file. History is capped at MAX_HISTORY before being sent to the LLM to prevent unbounded context growth.

**VCS-agnostic registry sync** -- Uses native Git operations rather than vendor-specific APIs, making it compatible with all three VCS systems supported by TFC/TFE.

**Atomic catalog writes** -- Module catalog is written via tempfile + os.replace to prevent partial writes from corrupting the index.

**Dry run mode** -- DRY_RUN=true skips all LLM API calls, making the CLI fully testable without credentials.

**Test coverage** -- over 90% code coverage; tests across all service layers using pytest and monkeypatch, with no real API or filesystem calls.

## Security & Privacy

terragenai runs entirely on your local machine. No module metadata, infrastructure context, or chat history is sent to any third-party service other than the configured LLM API endpoint.

The LLM endpoint is fully configurable, allowing organizations to point the tool at any compatible API — including self-hosted or privately hosted models, or any other provider that meets internal security and compliance requirements. The vector index and module catalog are stored locally on disk and never leave the machine.

## Tech Stack

| Area | Technology |
|---|---|
| Language | Python 3.9+ |
| CLI | argparse, rich, PyPi |
| IaC | Terraform Cloud/Enterprise API, python-hcl2 |
| Vector search | FAISS IndexFlatL2 |
| Embeddings | Configurable (default: text-embedding-3-small) |
| LLM | Configurable (default: gpt-3.5-turbo) |
| Testing | pytest, pytest-cov |
| Packaging | setuptools, setuptools-scm, PyPI |


## Usage

### Installation
```
% pip install terragenai
```

### Setup
```
% terragenai --configure
Enter TF_ORG []: 
Enter TF_REGISTRY_DOMAIN [app.terraform.io]: 
Enter TF_API_TOKEN []: 
Enter GIT_CLONE_TOKEN []: 
Enter LLM_API_KEY []: 
Saved configuration.
```
```
% terragenai --sync
Fetching Terraform modules for org: my-org
Found 12 module(s)
Processing my-org/vpc/aws
  Indexed v1.0.0
  Indexed v1.1.0
Processing my-org/ec2-module/aws
  Indexed v2.0.0
...

Done. 12 repo(s) indexed.
Catalog written to ~/.terragenai/catalog/modules.json
```

### Chat
```
% terragenai
TerragenAI Chat started. Type 'exit' to quit.

You: create 2 ec2 instances in us-west-2
Thinking...

Assistant: 

  module ec2 {
    source         = app.terraform.io/my-org/ec2-module/aws
    ami            = ami-0123456789abcdef0 
    instance_type  = t3.micro
    key_name       = my-ssh-key
    region         = us-west-2
    instance_count = 2
  }

You: exit
% 
```

## Common Flags

```bash
terragenai --help
terragenai --version
terragenai --configure
terragenai --sync
```

### --configure
- `--configure` saves settings to your OS-specific user config directory. It prompts for Terraform Enterprise/Cloud and LLM settings.

| Variable | Description |
|---|---|
| `TF_ORG` | Your Terraform Cloud/Enterprise organization name |
| `TF_REGISTRY_DOMAIN` | Registry domain (default: app.terraform.io) |
| `TF_API_TOKEN` | TFC/TFE API token |
| `GIT_CLONE_TOKEN` | Git token for cloning private module repos |
| `LLM_API_KEY` | LLM provider API key |

### --sync
- `--sync` fetches all modules from your Terraform Cloud/Enterprise private registry, clones each repo, parses Terraform variables, and builds a local module catalog used for AI-powered code generation. Run this before starting a chat session, and re-run it whenever your registry modules change.


## Overrides:
- `TERRAGENAI_HOME` to place both files in a single custom directory.
- `TERRAGENAI_CONFIG_FILE` to set an exact config file path.
- `TERRAGENAI_HISTORY_FILE` to set an exact history file path.