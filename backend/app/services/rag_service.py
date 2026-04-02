from openai import OpenAI

from app.core.config import settings
from app.services.retrieval_service import retrieve_relevant_chunks

client = OpenAI(api_key=settings.openai_api_key)

SYSTEM_PROMPT = """You are a document assistant. You answer questions strictly based on the context provided below.

Rules you must follow:
- Only use information explicitly stated in the provided context.
- Do not use any knowledge from your training data.
- If the context does not contain enough information to answer the question, respond with exactly: "I don't know based on the provided documents."
- Do not speculate, infer, or add information that is not in the context.
- Do not say things like "based on my knowledge" or "generally speaking"."""


def generate_rag_response(query: str) -> dict:
    chunks = retrieve_relevant_chunks(query)

    if not chunks:
        return {
            "question": query,
            "answer": "I don't know based on the provided documents.",
            "sources": [],
        }

    context = "\n\n".join(chunks)
    user_prompt = f"Context:\n{context}\n\nQuestion: {query}"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    return {
        "question": query,
        "answer": response.choices[0].message.content,
        "sources": chunks,
    }
