import os
import boto3


class SQSClient:
    def __init__(self):
        session = boto3.Session(profile_name=os.getenv("AWS_PROFILE"))
        self._client = session.client("sqs", region_name=os.getenv("AWS_REGION"))
        self._queue_url = os.getenv("SQS_QUEUE_URL")

    def receive_messages(self):
        response = self._client.receive_message(
            QueueUrl=self._queue_url,
            MaxNumberOfMessages=10
        )

        return response

    def delete_message(self, receipt_handle):
        self._client.delete_message(
            QueueUrl=self._queue_url,
            ReceiptHandle=receipt_handle
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self._client.close()
