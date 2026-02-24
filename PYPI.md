# terragenai 

A generative AI CLI tool that builds terraform configurations using a Terraform Enterprise or Cloud organization's private registry modules.

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
Enter OPENAI_API_KEY []: 
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

  module "ec2" {
    source         = "app.terraform.io/my-org/ec2-module/aws"
    ami            = "ami-0123456789abcdef0" 
    instance_type  = "t3.micro"
    key_name       = "my-ssh-key"
    region         = "us-west-2"
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
| `TF_ORG` | Your Terraform Cloud/Enterprise organisation name |
| `TF_REGISTRY_DOMAIN` | Registry domain (default: app.terraform.io) |
| `TF_API_TOKEN` | TFC/TFE API token |
| `GIT_CLONE_TOKEN` | Git token for cloning private module repos |
| `LLM_API_KEY` | OpenAI API key |

### --sync
- `--sync` fetches all modules from your Terraform Cloud/Enterprise private registry, clones each repo, parses Terraform variables, and builds a local module catalog used for AI-powered code generation. Run this before starting a chat session, and re-run it whenever your registry modules change.


## Overrides:
- `TERRAGENAI_HOME` to place both files in a single custom directory.
- `TERRAGENAI_CONFIG_FILE` to set an exact config file path.
- `TERRAGENAI_HISTORY_FILE` to set an exact history file path.