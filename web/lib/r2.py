import os
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


def download_audio_file(audio_bucket_key: str, output_dir: str = "/tmp") -> str:
    """
    Download the audio file from R2 and process clips.

    Args:
        audio_bucket_key (str): The key of the audio file in the R2 bucket.
        clips (list): List of clip objects to process.

    Raises:
        Exception: If there's an error downloading or processing the audio file.
    """
    audio_file_path = f"{output_dir}/{audio_bucket_key}"
    os.makedirs(os.path.dirname(audio_file_path), exist_ok=True)

    try:
        # Download the file directly using boto3
        r2.download_file(bucket_name, audio_bucket_key, audio_file_path)
        print(f"Successfully downloaded audio file to {audio_file_path}")
        return audio_file_path
    except ClientError as e:
        print(f"Error downloading audio file: {str(e)}")
        raise
    except Exception as e:
        print(f"Unexpected error in download_audio_file: {str(e)}")
        raise


def upload_file_to_r2(file_path: str, bucket_key: str):
    try:
        with open(file_path, "rb") as file:
            r2.upload_fileobj(file, bucket_name, bucket_key)
        print(f"Successfully uploaded {file_path} to R2 with key {bucket_key}")
    except Exception as e:
        print(f"Error uploading file to R2: {str(e)}")
        raise


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


def get_audio_transcript_key(audio_bucket_key: str) -> bool:
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


def get_audio_transcript(transcript_bucket_key: str):
    """
    Retrieve and parse the audio transcript from the R2 bucket.

    Args:
        transcript_bucket_key (str): The key of the transcript in the R2 bucket.

    Returns:
        dict: The parsed transcript JSON, or None if not found or on error.

    Raises:
        Exception: If there's an error retrieving or parsing the transcript.
    """
    try:
        # Retrieve the transcript object
        response = r2.get_object(Bucket=bucket_name, Key=transcript_bucket_key)

        # Read the content of the object
        transcript_content = response["Body"].read().decode("utf-8")

        print(f"Retrieved transcript content for key: {transcript_bucket_key}")

        # Parse the JSON content
        transcript_json = json.loads(transcript_content)
        return transcript_json

    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            print(f"Transcript not found for key: {transcript_bucket_key}")
            return None
        else:
            print(f"Error retrieving transcript: {str(e)}")
            raise

    except json.JSONDecodeError as e:
        print(f"Error parsing transcript JSON: {str(e)}")
        return None

    except Exception as e:
        print(f"Unexpected error in get_audio_transcript: {str(e)}")
        raise
