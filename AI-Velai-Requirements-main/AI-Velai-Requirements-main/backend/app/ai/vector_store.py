import hashlib

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import settings
from app.models import Job


client = QdrantClient(url=settings.qdrant_url, timeout=2)


def ensure_collection() -> None:
    existing = [collection.name for collection in client.get_collections().collections]
    if settings.qdrant_collection in existing:
        return
    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config=VectorParams(size=settings.vector_size, distance=Distance.COSINE),
    )


def upsert_job(job: Job) -> None:
    try:
        ensure_collection()
        text = f"{job.title}\n{job.generated_description}\n{job.skills or ''}"
        client.upsert(
            collection_name=settings.qdrant_collection,
            points=[
                PointStruct(
                    id=job.id,
                    vector=deterministic_vector(text, settings.vector_size),
                    payload={
                        "job_id": job.id,
                        "company_id": job.company_id,
                        "title": job.title,
                        "status": job.status,
                    },
                )
            ],
        )
    except Exception:
        # Qdrant should not block the core hiring workflow during local development.
        return


def deterministic_vector(text: str, size: int) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    while len(values) < size:
        for byte in digest:
            values.append((byte / 127.5) - 1.0)
            if len(values) == size:
                break
        digest = hashlib.sha256(digest).digest()
    return values
