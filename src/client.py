def send_message(history: list[dict]) -> str:
    user_prompt = ""
    for message in reversed(history):
        if message.get("role") == "user":
            user_prompt = message.get("content", "")
            break

    return (
        "Generated starter Terraform (general resource blocks):\n\n"
        "```hcl\n"
        'resource "aws_instance" "example" {\n'
        '  ami           = "ami-0123456789abcdef0"\n'
        '  instance_type = "t3.micro"\n'
        "}\n"
        "```\n\n"
        f"Input interpreted: {user_prompt or '(none)'}"
    )
