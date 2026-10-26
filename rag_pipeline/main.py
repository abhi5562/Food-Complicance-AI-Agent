import json

from botocore.exceptions import ClientError
from dotenv import load_dotenv

from clients.db_client import DBClient
from clients.sqs_client import SQSClient
from ingestion import insert_vectors, update_vectors, delete_vectors


def process_record(record):
    event_name = record["eventName"]
    if not event_name.startswith(("ObjectCreated:", "ObjectRemoved:")):
        return

    bucket = record["s3"]["bucket"]["name"]
    s3_key = record["s3"]["object"]["key"]
    sequencer = record["s3"]["object"]["sequencer"]
    incoming_sequence = int(sequencer, 16)

    with DBClient() as db:
        last_sequencer = db.get_last_sequencer(s3_key)
        if last_sequencer is not None and incoming_sequence <= int(last_sequencer, 16):
            print(f"Skipping stale or duplicate event: {event_name}, s3_key={s3_key}")
            return

        print(f"Processing event: {event_name}, s3_key={s3_key}")
        document = db.get_by_s3_key(s3_key)
        if event_name.startswith("ObjectCreated:"):
            try:
                if document is None:
                    insert_vectors(bucket=bucket, s3_key=s3_key, db=db)
                else:
                    update_vectors(document_id=document[0], bucket=bucket, s3_key=s3_key, db=db)
            except ClientError as error:
                # The file may have been deleted before its upload event was processed.
                if error.response["Error"]["Code"] in ("NoSuchKey", "404"):
                    print(f"Skipping upload event because the S3 file is missing: {s3_key}")
                    return
                raise
        elif document is not None:
            delete_vectors(document_id=document[0], db=db)
        else:
            # Remember the delete so an older upload event is skipped.
            db.create_tombstone(s3_key, sequencer)

        # Save the sequencer only after the event is processed successfully.
        db.record_sequencer(s3_key, sequencer)


def main():
    load_dotenv()
    with SQSClient() as sqs:
        response = sqs.receive_messages()
        messages = response.get("Messages", [])
        if not messages:
            print("No Events Recorded")

        for message in messages:
            body = json.loads(message["Body"])
            if body.get("Event") == "s3:TestEvent":
                print("Received S3 test event")
            else:
                process_record(body["Records"][0])
            # Acknowledge test and stale events too. Exceptions leave the message queued.
            sqs.delete_message(message["ReceiptHandle"])


if __name__ == "__main__":
    main()
