import logging
import os
import time

from fastapi import FastAPI
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig
from auth import verify_api_key
from fastapi import Depends


app = FastAPI()

# =========================
# LOG CONFIG
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# =========================
# PROXY CONFIG (WEB SHARE)
# =========================

PROXY_USER = os.getenv("PROXY_USER")
PROXY_PASS = os.getenv("PROXY_PASS")

api = YouTubeTranscriptApi(
    proxy_config=WebshareProxyConfig(
        proxy_username=PROXY_USER,
        proxy_password=PROXY_PASS,
        filter_ip_locations=["br"],
    )
)


# =========================
# HELPERS
# =========================

def format_transcript(transcript):
    return " ".join([item.text for item in transcript])


def fetch_transcript_with_minutes(video_id: str, retries=4):
    for attempt in range(1, retries + 1):
        try:
            transcript = api.fetch(video_id, languages=["pt"])

            duration_minutes = None

            try:
                if transcript:
                    last = transcript[-1]
                    duration_seconds = last.start + last.duration
                    duration_minutes = round(duration_seconds / 60, 2)
            except Exception as e:
                logging.warning(f"Duration calc failed for {video_id}: {e}")

            formatted = format_transcript(transcript)

            return {
                "text": formatted,
                "duration_minutes": duration_minutes
            }

        except Exception as e:
            logging.warning(
                f"Attempt {attempt}/{retries} failed for {video_id}: {e}"
            )

            if attempt == retries:
                raise e

            backoff = 0.5 * attempt
            time.sleep(backoff)


def fetch_transcript(video_id: str, retries=4):
    for attempt in range(1, retries + 1):

        try:

            transcript = api.fetch(video_id, languages=["pt"])

            return format_transcript(transcript)

        except Exception as e:

            logging.warning(
                f"Attempt {attempt}/{retries} failed for {video_id}: {e}"
            )

            if attempt == retries:
                raise e

            backoff = 0.5 * attempt
            time.sleep(backoff)


# =========================
# API ENDPOINT
# =========================

@app.get("/api/v1/crawl/transcript/{video_id}")
def get_transcript(video_id: str, _=Depends(verify_api_key)):
    start = time.time()

    try:
        transcript = fetch_transcript_with_minutes(video_id)

        return {
            "videoId": video_id,
            "transcript": transcript["text"],
            "video_duration_minutes": transcript["duration_minutes"],
            "duration_ms": int((time.time() - start) * 1000)
        }

    except Exception as e:

        logging.error(f"Transcript error {video_id}: {e}")

        return {
            "videoId": video_id,
            "transcript": None,
            "error": str(e)
        }


# =========================
# HEALTHCHECK
# =========================

@app.get("/health")
def health():
    return {"status": "ok"}


