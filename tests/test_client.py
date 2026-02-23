from unittest.mock import MagicMock

from src import client


def _mock_vector_store(
    retrieved_modules="[]", reply='```hcl\nresource "aws_instance" "example" {}\n```'
):
    vector_store = MagicMock()
    vector_store.retrieve_modules.return_value = retrieved_modules
    vector_store.llm.generate.return_value = reply
    return vector_store


# ------------------------------
# send_message
# ------------------------------


def test_send_message_returns_llm_reply():
    vector_store = _mock_vector_store(reply="some terraform code")
    result = client.send_message("create a vpc", vector_store)
    assert result == "some terraform code"


def test_send_message_calls_retrieve_modules_with_prompt():
    vector_store = _mock_vector_store()
    client.send_message("create an eks cluster", vector_store)
    vector_store.retrieve_modules.assert_called_once_with("create an eks cluster")


def test_send_message_calls_llm_generate():
    vector_store = _mock_vector_store()
    client.send_message("create a vpc", vector_store)
    vector_store.llm.generate.assert_called_once()


def test_send_message_includes_system_prompt_with_inventory():
    retrieved = '[{"source": "app.terraform.io/my-org/vpc/aws"}]'
    vector_store = _mock_vector_store(retrieved_modules=retrieved)
    client.send_message("create a vpc", vector_store)

    messages = vector_store.llm.generate.call_args[0][0]
    system_message = messages[0]
    assert system_message["role"] == "system"
    assert retrieved in system_message["content"]


def test_send_message_includes_user_prompt_in_messages():
    vector_store = _mock_vector_store()
    client.send_message("create an s3 bucket", vector_store)

    messages = vector_store.llm.generate.call_args[0][0]
    user_message = messages[-1]
    assert user_message["role"] == "user"
    assert user_message["content"] == "create an s3 bucket"


def test_send_message_returns_error_string_on_llm_exception():
    vector_store = _mock_vector_store()
    vector_store.llm.generate.side_effect = Exception("timeout")

    result = client.send_message("create a vpc", vector_store)
    assert "Error generating Terraform" in result
    assert "timeout" in result


def test_send_message_handles_empty_retrieved_modules():
    vector_store = _mock_vector_store(retrieved_modules=None, reply="no modules found")
    result = client.send_message("create a vpc", vector_store)
    assert result == "no modules found"
