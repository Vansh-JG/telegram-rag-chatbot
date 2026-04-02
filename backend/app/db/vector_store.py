from functools import reduce
from operator import and_, or_

import weaviate.classes as wvc

from app.db.weaviate_client import client


def _collection_name(name: str) -> str:
    return name.capitalize()


def get_or_create_collection(name: str):
    col_name = _collection_name(name)
    if not client.collections.exists(col_name):
        client.collections.create(
            name=col_name,
            vectorizer_config=wvc.config.Configure.Vectorizer.none(),
        )
    return client.collections.get(col_name)


def get_or_create_telegram_collection():
    collection_name = "TelegramChunk"
    if not client.collections.exists(collection_name):
        client.collections.create(
            name=collection_name,
            vectorizer_config=wvc.config.Configure.Vectorizer.none(),
            properties=[
                wvc.config.Property(name="chunk_text", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="chat_id", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="chat_type", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="chat_name", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="sender_ids", data_type=wvc.config.DataType.TEXT_ARRAY),
                wvc.config.Property(name="primary_speaker_id", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="mentions_user_ids", data_type=wvc.config.DataType.TEXT_ARRAY),
                wvc.config.Property(name="timestamp_start", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="timestamp_end", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="source", data_type=wvc.config.DataType.TEXT),
            ],
        )
    return client.collections.get(collection_name)


def store_embeddings(
    collection_name: str,
    chunks: list[str],
    embeddings: list[list[float]],
    doc_id: str,
):
    collection = get_or_create_collection(collection_name)
    with collection.batch.dynamic() as batch:
        for chunk, embedding in zip(chunks, embeddings):
            batch.add_object(
                properties={"text": chunk, "doc_id": doc_id},
                vector=embedding,
            )


def query_collection(
    collection_name: str,
    query_embedding: list[float],
    top_k: int = 5,
) -> list[tuple[str, float]]:
    collection = get_or_create_collection(collection_name)
    results = collection.query.near_vector(
        near_vector=query_embedding,
        limit=top_k,
        return_properties=["text"],
        return_metadata=wvc.query.MetadataQuery(distance=True),
    )
    return [(obj.properties["text"], obj.metadata.distance) for obj in results.objects]


def store_telegram_chunks(chunks: list[dict]) -> int:
    collection = get_or_create_telegram_collection()
    stored_count = 0

    with collection.batch.dynamic() as batch:
        for chunk in chunks:
            embedding = chunk.get("embedding")
            if embedding is None:
                continue

            properties = {
                "chunk_text": chunk["chunk_text"],
                "chat_id": chunk["chat_id"],
                "chat_type": chunk["chat_type"],
                "chat_name": chunk["chat_name"],
                "sender_ids": chunk["sender_ids"],
                "primary_speaker_id": chunk["primary_speaker_id"],
                "mentions_user_ids": chunk["mentions_user_ids"],
                "timestamp_start": chunk["timestamp_start"],
                "timestamp_end": chunk["timestamp_end"],
                "source": chunk["source"],
            }
            batch.add_object(properties=properties, vector=embedding)
            stored_count += 1

    return stored_count


def _build_telegram_filters(filters: dict | None):
    if not filters:
        return None

    query_filters = []

    sender_id = filters.get("sender_ids")
    if sender_id:
        query_filters.append(
            wvc.query.Filter.by_property("sender_ids").contains_any([sender_id])
        )

    chat_ids = [chat_id for chat_id in filters.get("chat_id_in", []) if chat_id]
    if chat_ids:
        chat_filters = [
            wvc.query.Filter.by_property("chat_id").equal(chat_id) for chat_id in chat_ids
        ]
        query_filters.append(reduce(or_, chat_filters))

    if not query_filters:
        return None

    return reduce(and_, query_filters)


def query_telegram_chunks(
    embedding: list[float],
    filters: dict | None = None,
    top_k: int = 5,
) -> list[dict]:
    collection = get_or_create_telegram_collection()
    results = collection.query.near_vector(
        near_vector=embedding,
        limit=top_k,
        filters=_build_telegram_filters(filters),
        return_properties=[
            "chunk_text",
            "chat_id",
            "chat_type",
            "chat_name",
            "sender_ids",
            "primary_speaker_id",
            "mentions_user_ids",
            "timestamp_start",
            "timestamp_end",
            "source",
        ],
        return_metadata=wvc.query.MetadataQuery(distance=True),
    )

    chunks = []
    for obj in results.objects:
        chunk = dict(obj.properties)
        chunk["distance"] = obj.metadata.distance
        chunks.append(chunk)

    return chunks
