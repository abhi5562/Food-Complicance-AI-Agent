from hashlib import sha256
from contextlib import nullcontext
from uuid import uuid4

from langchain_openai import OpenAIEmbeddings

from clients.db_client import DBClient
from clients.pinecone_client import PineconeClient
from process_pdf import pdf_to_chunks


def insert_vectors(bucket: str, s3_key: str, db=None):
    s3_link = f"s3://{bucket}/{s3_key}"
    chunks = pdf_to_chunks(s3_link=s3_link)

    if not chunks:
        raise ValueError("The PDF has no text chunks to insert.")

    document_id = uuid4()
    texts = [chunk.page_content for chunk in chunks]
    content_hash = sha256("\n\n".join(texts).encode("utf-8")).hexdigest()
    embeddings = OpenAIEmbeddings()
    vectors = []

    for index, chunk in enumerate(chunks):
        vectors.append({
            "id": f"{document_id}:{index}",
            "values": embeddings.embed_query(chunk.page_content),
            "metadata": {
                **chunk.metadata,
                "document_id": str(document_id),
                "text": chunk.page_content
            },
        })

    with PineconeClient() as pinecone:
        with (DBClient() if db is None else nullcontext(db)) as db:
            db.add_to_db(
                id=document_id,
                s3_key=s3_key,
                content_hash=content_hash,
                status="Indexed",
                last_sequencer=None,
                chunk_count=len(chunks),
            )
            pinecone.upsert_vectors(vectors)

    print(f"Insert completed: document_id={document_id}, vector_count={len(chunks)}")
    return document_id


def update_vectors(document_id: str, bucket: str, s3_key: str, db=None):
    s3_link = f"s3://{bucket}/{s3_key}"
    chunks = pdf_to_chunks(s3_link=s3_link)

    if not chunks:
        raise ValueError("The PDF has no text chunks to insert.")

    texts = [chunk.page_content for chunk in chunks]
    content_hash = sha256("\n\n".join(texts).encode("utf-8")).hexdigest()
    embeddings = OpenAIEmbeddings()
    vectors = []

    for index, chunk in enumerate(chunks):
        vectors.append({
            "id": f"{document_id}:{index}",
            "values": embeddings.embed_query(chunk.page_content),
            "metadata": {
                **chunk.metadata,
                "document_id": str(document_id),
                "text": chunk.page_content
            },
        })

    with PineconeClient() as pinecone:
        with (DBClient() if db is None else nullcontext(db)) as db:
            previous_chunk_count = db.get_chunk_count(document_id)
            pinecone.upsert_vectors(vectors)

            old_ids = [
                f"{document_id}:{index}"
                for index in range(len(chunks), previous_chunk_count)
            ]

            #Delete existing vectors if the current_chunk_count < previous_chunk_count
            if old_ids:
                pinecone.delete_vectors(ids=old_ids)

            db.update_document(
                document_id=document_id,
                s3_key=s3_key,
                content_hash=content_hash,
                status="Indexed",
                chunk_count=len(chunks),
            )

    print(f"Update completed: document_id={document_id}, vector_count={len(chunks)}")
    return document_id


def delete_vectors(document_id: str, db=None):
    with (DBClient() if db is None else nullcontext(db)) as db:
        chunk_count = db.get_chunk_count(document_id)
        ids = [f"{document_id}:{index}" for index in range(chunk_count)]

        if ids:
            with PineconeClient() as pinecone:
                pinecone.delete_vectors(ids=ids)

        # Preserve the manifest row so delayed events can still be rejected.
        db.mark_document_deleted(document_id)

    print(f"Delete completed: document_id={document_id}, vector_count={chunk_count}")
