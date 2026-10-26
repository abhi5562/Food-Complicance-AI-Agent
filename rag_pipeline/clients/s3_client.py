import os
from pathlib import Path
from urllib.parse import urlsplit

import boto3


class S3Client:
    def __init__(self):
        session = boto3.Session(profile_name=os.getenv("AWS_PROFILE"))
        self._client = session.client("s3", region_name=os.getenv("AWS_REGION"))

    def download_pdf(self, s3_link):
        """Download a PDF to the project's documents folder and return its path."""
        location = urlsplit(s3_link)
        key = location.path[1:]
        documents_dir = Path(__file__).resolve().parent.parent / "documents"
        documents_dir.mkdir(exist_ok=True)
        file_path = documents_dir / Path(key).name
        print(f"Downloading PDF: bucket={location.netloc}, key={key}")
        self._client.download_file(
            location.netloc,
            key,
            str(file_path),
        )
        return file_path

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self._client.close()
