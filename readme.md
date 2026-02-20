# terragenai 

A generative AI CLI tool that builds terraform configurations using Terraform Enterprise or Cloud private registry modules.

## How to Install

```bash
pip install terragenai
terragenai
```

## Common Flags

```bash
terragenai --help
terragenai -m src.main --version
terragenai -m src.main --configure
```

`--configure` saves settings to your OS-specific user config directory.

Overrides:
- `TERRAGENAI_HOME` to place both files in a single custom directory.
- `TERRAGENAI_CONFIG_FILE` to set an exact config file path.
- `TERRAGENAI_HISTORY_FILE` to set an exact history file path.

## Usage
```
% terragenai
LLM CLI started. Type 'exit' to quit.

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