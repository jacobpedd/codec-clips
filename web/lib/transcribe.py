from django.conf import settings
import assemblyai as aai
from web.lib.r2 import get_audio_transcript, handle_r2_transcript_upload

aai.settings.api_key = settings.ASSEMBLYAI_API_KEY
transcriber = aai.Transcriber()
config = aai.TranscriptionConfig(
    speaker_labels=True,
)


def transcribe(audio_bucket_key: str) -> str:
    """Transcribe the audio file and return the transcript."""
    # Check if the audio file has been transcribed already
    transcript_bucket_key = get_audio_transcript(audio_bucket_key)
    if transcript_bucket_key:
        return transcript_bucket_key

    # Transcribe the audio file using the bucket's public URL and AssemblyAI
    config = aai.TranscriptionConfig(speaker_labels=True)
    bucket_audio_url = f"{settings.R2_BUCKET_URL}/{audio_bucket_key}"
    print(bucket_audio_url)
    transcript = transcriber.transcribe(bucket_audio_url, config)

    print(transcript)

    utterances = []
    for utterance in transcript.utterances:
        words = []
        for word in utterance.words:
            words.append(
                {
                    "text": word.text,
                    "start": word.start,
                    "end": word.end,
                    "speaker": word.speaker,
                }
            )
        utterances.append(
            {
                "text": utterance.text,
                "start": utterance.start,
                "end": utterance.end,
                "speaker": utterance.speaker,
                "words": words,
            }
        )

    transcript_bucket_key = handle_r2_transcript_upload(utterances, audio_bucket_key)
    return transcript_bucket_key
