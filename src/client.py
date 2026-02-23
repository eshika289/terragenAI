from .services.vector_store.faiss_store import FaissService


def send_message(user_prompt: str, history: list[dict], vector_store: FaissService) -> str:


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


    try:
        reply = vector_store.llm.generate(messages)
    except Exception as e:
        reply = f"⚠ Error generating Terraform: {e}"


    return reply
