from unittest.mock import MagicMock

from src import client


def _mock_vector_store(
    retrieved_modules="[]", reply='```hcl\nresource "aws_instance" "example" {}\n```'
):
    vector_store = MagicMock()
    vector_store.retrieve_modules.return_value = retrieved_modules
    vector_store.llm.generate.return_value = reply
    return vector_store


SAMPLE_HISTORY = [{"role": "user", "content": "create a vpc"}]


# ------------------------------
# send_message
# ------------------------------

def test_send_message_returns_llm_reply():
    vector_store = _mock_vector_store(reply="some terraform code")
    result = client.send_message("create a vpc", SAMPLE_HISTORY, vector_store)
    assert result == "some terraform code"


def test_send_message_calls_retrieve_modules_with_prompt():
    vector_store = _mock_vector_store()
    client.send_message("create an eks cluster", SAMPLE_HISTORY, vector_store)
    vector_store.retrieve_modules.assert_called_once_with("create an eks cluster")


def test_send_message_calls_llm_generate():
    vector_store = _mock_vector_store()
    client.send_message("create a vpc", SAMPLE_HISTORY, vector_store)
    vector_store.llm.generate.assert_called_once()


def test_send_message_includes_system_prompt_with_inventory():
    retrieved = '[{"source": "app.terraform.io/my-org/vpc/aws"}]'
    vector_store = _mock_vector_store(retrieved_modules=retrieved)
    client.send_message("create a vpc", SAMPLE_HISTORY, vector_store)

    messages = vector_store.llm.generate.call_args[0][0]
    system_message = messages[0]
    assert system_message["role"] == "system"
    assert retrieved in system_message["content"]


def test_send_message_includes_history_in_messages():
    vector_store = _mock_vector_store()
    history = [
        {"role": "user", "content": "create a vpc"},
        {"role": "assistant", "content": "here is your vpc"},
    ]
    client.send_message("add a subnet", history, vector_store)

    messages = vector_store.llm.generate.call_args[0][0]
    assert {"role": "user", "content": "create a vpc"} in messages
    assert {"role": "assistant", "content": "here is your vpc"} in messages


def test_send_message_includes_user_prompt_in_messages():
    vector_store = _mock_vector_store()
    history = [{"role": "user", "content": "create an s3 bucket"}]
    client.send_message("create an s3 bucket", history, vector_store)

    messages = vector_store.llm.generate.call_args[0][0]
    assert any(
        m["role"] == "user" and m["content"] == "create an s3 bucket"
        for m in messages
    )


def test_send_message_returns_error_string_on_llm_exception():
    vector_store = _mock_vector_store()
    vector_store.llm.generate.side_effect = Exception("timeout")

    result = client.send_message("create a vpc", SAMPLE_HISTORY, vector_store)
    assert "Error generating Terraform" in result
    assert "timeout" in result


def test_send_message_handles_empty_retrieved_modules():
    vector_store = _mock_vector_store(retrieved_modules=None, reply="no modules found")
    result = client.send_message("create a vpc", SAMPLE_HISTORY, vector_store)
    assert result == "no modules found"


def test_send_message_empty_history():
    vector_store = _mock_vector_store(reply="terraform code")
    result = client.send_message("create a vpc", [], vector_store)
    assert result == "terraform code"
