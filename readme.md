# terragenai 

A generative AI CLI tool that builds terraform configurations using a Terraform Enterprise or Cloud organization's private registry modules.

## Common Flags

```bash
terragenai --help
terragenai --version
terragenai --configure
terragenai --sync
```

`--configure` saves settings to your OS-specific user config directory.
It prompts for Terraform-related settings (`TF_ORG`, `TF_REGISTRY_DOMAIN`, `TF_API_TOKEN`, `GIT_CLONE_TOKEN`).

`--sync` fetches all modules from your Terraform Cloud/Enterprise private registry, clones each repo, parses Terraform variables, and builds a local module catalog used for AI-powered code generation. Run this before starting a chat session, and re-run it whenever your registry modules change.

Overrides:
- `TERRAGENAI_HOME` to place both files in a single custom directory.
- `TERRAGENAI_CONFIG_FILE` to set an exact config file path.
- `TERRAGENAI_HISTORY_FILE` to set an exact history file path.

## Usage
```
% pip install terragenai
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