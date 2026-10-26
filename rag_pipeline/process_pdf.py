import pymupdf
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from clients.s3_client import S3Client


def pdf_to_chunks(s3_link) -> list[Document]:
    """Download an S3 PDF and return text chunks with source and page metadata."""
    with S3Client() as s3:
        file_path = s3.download_pdf(s3_link)

    with pymupdf.open(file_path) as pdf:
        documents = [
            Document(
                page_content=page.get_text(),
                metadata={"source": s3_link, "page": page.number},
            )
            for page in pdf
        ]

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    return splitter.split_documents(documents)
