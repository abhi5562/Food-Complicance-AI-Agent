import os
from hashlib import sha256
from uuid import uuid4

import psycopg

class DBClient:
    def __init__(self, dsn=None, connect_timeout=10):
        if dsn is None:
            dsn = os.getenv("DATABASE_URL")
        if not dsn:
            raise ValueError("Set DATABASE_URL in .env or pass a DSN to DBClient.")
        self._connection = psycopg.connect(dsn, connect_timeout=connect_timeout)

    def add_to_db(self, id, s3_key, content_hash, status, last_sequencer, chunk_count):
        row = self.fetch_one(
            """
            INSERT INTO documents
                (id, s3_key, content_hash, status, last_sequencer, chunk_count)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (id, s3_key, content_hash, status, last_sequencer, chunk_count),
        )
        return row[0]

    def s3_key_exists(self, s3_key) -> bool:
        row = self.fetch_one(
            "SELECT s3_key FROM documents WHERE s3_key = %s",
            (s3_key,),
        )
        return row is not None

    def get_by_s3_key(self, s3_key):
        return self.fetch_one(
            "SELECT * FROM documents WHERE s3_key = %s",
            (s3_key,),
        )

    def get_last_sequencer(self, s3_key):
        row = self.fetch_one(
            "SELECT last_sequencer FROM documents WHERE s3_key = %s",
            (s3_key,),
        )
        return row[0] if row else None

    def record_sequencer(self, s3_key, sequencer):
        """Record the sequencer after successful event processing."""
        self.execute(
            "UPDATE documents SET last_sequencer = %s WHERE s3_key = %s",
            (sequencer, s3_key),
        )

    def create_tombstone(self, s3_key, sequencer):
        """Remember a delete even when the create event has not been processed."""
        # A tombstone is a row that remembers a deleted file so older events are skipped.
        return self.add_to_db(
            id=uuid4(),
            s3_key=s3_key,
            content_hash=sha256(b"").hexdigest(),
            status="Deleted",
            last_sequencer=sequencer,
            chunk_count=0,
        )

    def get_chunk_count(self, document_id):
        row = self.fetch_one(
            "SELECT chunk_count FROM documents WHERE id = %s",
            (document_id,),
        )
        return row[0]

    def update_document(self, document_id, s3_key, content_hash, status, chunk_count):
        return self.execute(
            """
            UPDATE documents
            SET s3_key = %s, content_hash = %s, status = %s, chunk_count = %s
            WHERE id = %s
            """,
            (s3_key, content_hash, status, chunk_count, document_id),
        )

    def mark_document_deleted(self, document_id):
        return self.execute(
            """
            UPDATE documents SET status = 'Deleted', chunk_count = 0
            WHERE id = %s
            """,
            (document_id,),
        )

    def execute(self, query, params=None):
        # Run the query and return the number of rows affected.
        with self._connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.rowcount

    def fetch_one(self, query, params=None):
        # Run the query and return the first row, or None if no rows are found.
        with self._connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()

    def fetch_all(self, query, params=None):
        # Run the query and return all rows, or an empty list if no rows are found.
        with self._connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    def __enter__(self):
        self._connection.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        return self._connection.__exit__(exc_type, exc, tb)
