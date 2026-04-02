from app.services.embedding_service import generate_embeddings
from app.db.vector_store import query_collection

RELEVANCE_THRESHOLD = 1.8  # L2 distance; lower = more similar


def retrieve_relevant_chunks(query: str, top_k: int = 5) -> list[str]:
    query_embedding = generate_embeddings([query])[0]
    results = query_collection(
        collection_name="documents",
        query_embedding=query_embedding,
        top_k=top_k,
    )
    return [doc for doc, distance in results if distance < RELEVANCE_THRESHOLD]
