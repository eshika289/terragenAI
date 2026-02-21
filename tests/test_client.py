from src import client


def test_send_message_returns_starter_block_and_uses_latest_user_input():
    history = [
        {"role": "user", "content": "create ec2 instance"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "in us-west-2"},
    ]

    response = client.send_message(history)

    assert "Generated starter Terraform" in response
    assert 'resource "aws_instance" "example"' in response
    assert "Input interpreted: in us-west-2" in response


def test_send_message_handles_empty_history():
    response = client.send_message([])

    assert "Input interpreted: (none)" in response
