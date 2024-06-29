import hashlib
import json
import boto3
import requests
from django.conf import settings
from botocore.client import Config
from botocore.exceptions import ClientError

# Configure the R2 client
r2 = boto3.client(
    "s3",
    endpoint_url=settings.R2_URL,
    aws_access_key_id=settings.R2_ACCESS_KEY,
    aws_secret_access_key=settings.R2_SECRET_KEY,
    config=Config(signature_version="s3v4"),
)
bucket_name = settings.R2_BUCKET_NAME


def handle_r2_audio_upload(audio_url: str) -> str:
    """
    Check if the audio file exists in the R2 bucket and upload if it doesn't.

    Args:
        audio_url (str): The URL of the audio file to upload.

    Returns:
        str: The key of the file in the R2 bucket.

    Raises:
        Exception: If there's an error checking the bucket or uploading the file.
    """
    url_hash = hashlib.md5(audio_url.encode()).hexdigest()
    audio_bucket_key = f"audio-{url_hash}"

    try:
        # Check if the file already exists in the R2 bucket
        r2.head_object(Bucket=bucket_name, Key=audio_bucket_key)
        print(f"Audio file already exists in R2: {audio_bucket_key}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            # File doesn't exist, so we upload it
            with requests.get(audio_url, stream=True) as r:
                r.raise_for_status()
                r2.upload_fileobj(
                    Fileobj=r.raw,
                    Bucket=bucket_name,
                    Key=audio_bucket_key,
                )
            print(f"Uploaded audio file to R2: {audio_bucket_key}")
        else:
            raise

    return audio_bucket_key


def handle_r2_transcript_upload(transcript, audio_bucket_key) -> str:
    """
    Check if the transcript exists in the R2 bucket and upload if it doesn't.

    Args:
        transcript (obj): The transcript to upload.
        audio_bucket_key (str): The key of the audio file in the R2 bucket.

    Returns:
        str: The key of the transcript in the R2 bucket.

    Raises:
        Exception: If there's an error checking the bucket or uploading the transcript.
    """
    transcript_bucket_key = audio_bucket_key.replace("audio-", "transcript-")

    try:
        # Check if the transcript already exists in the R2 bucket
        r2.head_object(Bucket=bucket_name, Key=transcript_bucket_key)
        print(f"Transcript already exists in R2: {transcript_bucket_key}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            # Turn the transcript object into a json string
            transcript_json = json.dumps(transcript)
            # Upload the transcript to the R2 bucket
            r2.put_object(
                Body=transcript_json,
                Bucket=bucket_name,
                Key=transcript_bucket_key,
            )
            print(f"Uploaded transcript to R2: {transcript_bucket_key}")
        else:
            raise

    return transcript_bucket_key


def get_audio_transcript(audio_bucket_key: str) -> bool:
    """
    Check if the audio file has been transcribed in the R2 bucket.

    Args:
        audio_bucket_key (str): The key of the audio file in the R2 bucket.

    Returns:
        transcript_bucket_key (str): The key of the transcript in the R2 bucket.

    Raises:
        Exception: If there's an error checking the bucket.
    """
    transcript_bucket_key = audio_bucket_key.replace("audio-", "transcript-")

    try:
        # Check if the transcript already exists in the R2 bucket
        r2.head_object(Bucket=bucket_name, Key=transcript_bucket_key)
        print(f"Transcript already exists in R2: {transcript_bucket_key}")
        return transcript_bucket_key
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return None
        else:
            raise
