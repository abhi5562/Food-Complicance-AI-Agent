import os

from pinecone import Pinecone


class PineconeClient:
    def __init__(self):
        api_key = os.getenv("PINECONE_API_KEY")
        index_name = os.getenv("PINECONE_INDEX")

        self._client = Pinecone(api_key=api_key)
        try:
            self._index = self._client.Index(name=index_name)
        except Exception:
            self._close_client()
            raise

    def _close_client(self):
        # Some SDK versions only expose close() on the index connection.
        close = getattr(self._client, "close", None)
        if callable(close):
            close()

    def upsert_vectors(self, vectors, namespace=""):
        """Insert vectors or replace existing vectors with the same IDs."""
        if not vectors:
            raise ValueError("Provide at least one vector.")
        return self._index.upsert(vectors=vectors, namespace=namespace)

    def delete_vectors(self, ids, namespace=""):
        """Delete the specified vector IDs from a namespace."""
        if not ids or isinstance(ids, str):
            raise ValueError("Provide a non-empty list of vector IDs.")
        return self._index.delete(ids=ids, namespace=namespace)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            self._index.close()
        finally:
            self._close_client()
