from .services.vector_store.faiss_store import FaissService


def send_message(user_prompt: str, vector_store: FaissService) -> str:
    # user_prompt = ""
    # for message in reversed(history):
    #     if message.get("role") == "user":
    #         user_prompt = message.get("content", "")
    #         break

    # # Initialize conversation
    # if session_id not in state.conversations:
    #     state.conversations[session_id] = []

    # # Append user message
    # state.conversations[session_id].append({"role": "user", "content": user_prompt})

    # # Keep only last MAX_HISTORY messages
    # history = state.conversations[session_id][-state.MAX_HISTORY :]
    history = [{"role": "user", "content": user_prompt}]

    # Retrieve relevant modules - RAG
    retrieved_modules = vector_store.retrieve_modules(user_prompt)

    # - If no relevant modules are found, respond with a message indicating so.

    system_prompt = f"""
You are a Terraform code generator. 

Rules:
- Only use modules listed in the inventory
- Only use variables explicitly defined for each module
- Do NOT invent variables or modules
- Always use the exact module source string
- Respect required vs optional variables


Inventory:
{retrieved_modules}

Citations:
- For each module used in your response, include a comment line before each module with its vcs link.
Example: # Citation: <vcs_link>
"""

    messages = [{"role": "system", "content": system_prompt}] + history

    # logger.info("Full prompt sent to OpenAI: %s", messages)

    try:
        reply = vector_store.llm.generate(messages)
    except Exception as e:
        # logger.exception("❌ OpenAI request failed")
        reply = f"⚠ Error generating Terraform: {e}"

    # Append assistant message
    # state.conversations[session_id].append({"role": "assistant", "content": reply})

    return reply
