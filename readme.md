# terragenai 

A generative AI CLI tool that builds terraform configurations using Terraform Enterprise or Cloud private registry modules.

## Common Flags

```bash
terragenai --help
terragenai --version
terragenai --configure
```

`--configure` saves settings to your OS-specific user config directory.
It prompts for Terraform-related settings (`TF_ORG`, `TF_REGISTRY_DOMAIN`, `TF_API_TOKEN`, `GIT_CLONE_TOKEN`).

Overrides:
- `TERRAGENAI_HOME` to place both files in a single custom directory.
- `TERRAGENAI_CONFIG_FILE` to set an exact config file path.
- `TERRAGENAI_HISTORY_FILE` to set an exact history file path.

## Usage
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
    instance_type  = "t3.micro"
    instance_count = 2
  }

You: exit
% 
```
