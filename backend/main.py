
import os
import uuid
import shutil
import subprocess
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from deep_translator import GoogleTranslator
from sarvamai import SarvamAI

# Load environment variables from .env
load_dotenv()

# --------------------------------------------------
# APP CONFIGURATION
# --------------------------------------------------

app = FastAPI(
    title="VoxDub AI",
    description="Multilingual video dubbing and subtitle generation API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------
# LANGUAGES
# --------------------------------------------------

LANGUAGES = {
    "English": "en-IN",
    "Hindi": "hi-IN",
    "Bengali": "bn-IN",
    "Tamil": "ta-IN",
    "Telugu": "te-IN",
    "Kannada": "kn-IN",
    "Malayalam": "ml-IN",
    "Marathi": "mr-IN",
    "Gujarati": "gu-IN",
    "Punjabi": "pa-IN",
    "Odia": "od-IN",
}

# Compatible short speaker IDs for bulbul:v3.
# If Sarvam rejects a speaker, check the current
# supported-speaker list for your selected model.

LANGUAGE_SPEAKERS = {
    "English": "ishita",
    "Hindi": "priya",
    "Bengali": "roopa",
    "Tamil": "ritu",
    "Telugu": "neha",
    "Kannada": "ishita",
    "Malayalam": "pooja",
    "Marathi": "ritu",
    "Gujarati": "priya",
    "Punjabi": "roopa",
    "Odia": "pooja",
}

# --------------------------------------------------
# SARVAM CLIENT
# --------------------------------------------------

API_KEY = os.getenv("SARVAM_API_KEY")

sarvam_client = SarvamAI(
    api_subscription_key=API_KEY
) if API_KEY else None

# Store uploaded file information in memory.
# This is reset whenever the backend restarts.
uploaded_videos = {}

# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def check_sarvam_client():
    """Ensure the Sarvam API key is configured."""
    if not sarvam_client:
        raise HTTPException(
            status_code=500,
            detail=(
                "SARVAM_API_KEY is missing. "
                "Add it to backend/.env and restart the server."
            ),
        )


def check_ffmpeg():
    """Ensure FFmpeg is installed and available."""
    if shutil.which("ffmpeg") is None:
        raise HTTPException(
            status_code=500,
            detail="FFmpeg is not installed or not available in PATH.",
        )


def extract_audio(video_path: Path, audio_path: Path):
    """Extract audio from the uploaded video using FFmpeg."""
    check_ffmpeg()

    command = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        str(audio_path),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0 or not audio_path.exists():
        raise RuntimeError(
            "Audio extraction failed: " + result.stderr[-1500:]
        )


def transcribe_audio(audio_path: Path) -> str:
    """
    Transcribe audio using faster-whisper.
    Install faster-whisper if this import is unavailable.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "faster-whisper is not installed. "
            "Run: pip install faster-whisper"
        ) from exc

    model = WhisperModel(
        "base",
        device="cpu",
        compute_type="int8",
    )

    segments, _ = model.transcribe(
        str(audio_path),
        beam_size=5,
    )

    transcript = " ".join(
        segment.text.strip() for segment in segments
    ).strip()

    if not transcript:
        raise RuntimeError(
            "No speech was detected in the uploaded video."
        )

    return transcript


def translate_text(text: str, target_language: str) -> str:
    """Translate the transcript into the selected language."""
    if target_language not in LANGUAGES:
        raise ValueError("Unsupported target language.")

    target_code = LANGUAGES[target_language]

    # deep-translator uses language names/codes supported
    # by GoogleTranslator rather than Sarvam language codes.
    google_language_codes = {
        "English": "en",
        "Hindi": "hi",
        "Bengali": "bn",
        "Tamil": "ta",
        "Telugu": "te",
        "Kannada": "kn",
        "Malayalam": "ml",
        "Marathi": "mr",
        "Gujarati": "gu",
        "Punjabi": "pa",
        "Odia": "or",
    }

    translated = GoogleTranslator(
        source="auto",
        target=google_language_codes[target_language],
    ).translate(text)

    if not translated:
        raise RuntimeError("Translation returned empty text.")

    return translated


def synthesize_speech(
    text: str,
    target_language: str,
    output_audio_path: Path,
):
    """Generate speech using Sarvam Bulbul v3."""
    check_sarvam_client()

    speaker = LANGUAGE_SPEAKERS.get(target_language)
    language_code = LANGUAGES.get(target_language)

    if not speaker or not language_code:
        raise ValueError(
            f"Language configuration missing for {target_language}."
        )

    # Bulbul v3 supports limited text length per request.
    # Split long text into smaller chunks.
    chunks = [
        text[i:i + 450]
        for i in range(0, len(text), 450)
    ]

    generated_files = []

    for index, chunk in enumerate(chunks):
        try:
            response = sarvam_client.text_to_speech.convert(
                text=chunk,
                target_language_code=language_code,
                speaker=speaker,
                model="bulbul:v3",
            )
        except Exception as exc:
            raise RuntimeError(
                f"Sarvam TTS failed for {target_language} "
                f"with speaker '{speaker}': {exc}"
            ) from exc

        chunk_path = OUTPUT_DIR / (
            f"{output_audio_path.stem}_chunk_{index}.wav"
        )

        try:
            # Current Sarvam SDK responses commonly provide
            # base64-encoded audio in response.audios.
            import base64

            audio_list = getattr(response, "audios", None)

            if not audio_list:
                raise RuntimeError(
                    "Sarvam returned no audio data."
                )

            audio_bytes = base64.b64decode(audio_list[0])

            with open(chunk_path, "wb") as audio_file:
                audio_file.write(audio_bytes)

        except Exception as exc:
            raise RuntimeError(
                f"Could not save generated audio: {exc}"
            ) from exc

        generated_files.append(chunk_path)

    # Join chunks in order if the text was split.
    if len(generated_files) == 1:
        shutil.move(
            str(generated_files[0]),
            str(output_audio_path),
        )
    else:
        concat_file = OUTPUT_DIR / (
            f"{output_audio_path.stem}_concat.txt"
        )

        with open(concat_file, "w", encoding="utf-8") as file:
            for path in generated_files:
                file.write(
                    f"file '{path.as_posix()}'\n"
                )

        check_ffmpeg()

        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                str(output_audio_path),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(
                "Could not combine audio chunks: "
                + result.stderr[-1500:]
            )

        for path in generated_files:
            path.unlink(missing_ok=True)

        concat_file.unlink(missing_ok=True)


def create_dubbed_video(
    original_video: Path,
    dubbed_audio: Path,
    output_video: Path,
):
    """Replace the original video's audio with dubbed audio."""
    check_ffmpeg()

    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i", str(original_video),
            "-i", str(dubbed_audio),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            str(output_video),
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0 or not output_video.exists():
        raise RuntimeError(
            "Could not create dubbed video: "
            + result.stderr[-1500:]
        )


def create_srt(text: str, output_srt: Path):
    """Create a simple SRT subtitle file."""
    def format_time(seconds: int) -> str:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02}:{minutes:02}:{secs:02},000"

    lines = text.splitlines() if "\n" in text else [text]
    lines = [line.strip() for line in lines if line.strip()]

    with open(output_srt, "w", encoding="utf-8") as file:
        for index, line in enumerate(lines, start=1):
            start = (index - 1) * 5
            end = start + 5

            file.write(f"{index}\n")
            file.write(
                f"{format_time(start)} --> {format_time(end)}\n"
            )
            file.write(f"{line}\n\n")


# --------------------------------------------------
# API ROUTES
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "Welcome to VoxDub AI API",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "sarvam_configured": bool(sarvam_client),
        "ffmpeg_available": shutil.which("ffmpeg") is not None,
    }


@app.get("/languages")
def get_languages():
    return {
        "languages": list(LANGUAGES.keys())
    }


@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload a video and return its unique file ID."""
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Please select a video file.",
        )

    allowed_extensions = {
        ".mp4", ".mov", ".mkv", ".webm", ".avi"
    }

    extension = Path(file.filename).suffix.lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Unsupported video format.",
        )

    file_id = str(uuid.uuid4())
    video_path = UPLOAD_DIR / f"{file_id}{extension}"

    try:
        with open(video_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        await file.close()

    uploaded_videos[file_id] = {
        "original_name": file.filename,
        "video_path": video_path,
        "status": "uploaded",
    }

    return {
        "message": "Video uploaded successfully.",
        "file_id": file_id,
        "filename": file.filename,
        "status": "uploaded",
    }


@app.post("/dub/{file_id}")
def dub_video(file_id: str, target_language: str):
    """Transcribe, translate, synthesize and dub a video."""
    if file_id not in uploaded_videos:
        raise HTTPException(
            status_code=404,
            detail="Video not found. Please upload it again.",
        )

    if target_language not in LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported target language.",
        )

    video_path = uploaded_videos[file_id]["video_path"]

    audio_path = OUTPUT_DIR / f"{file_id}_original.wav"
    dubbed_audio_path = OUTPUT_DIR / f"{file_id}_dubbed.wav"
    output_video_path = OUTPUT_DIR / f"{file_id}_dubbed.mp4"
    subtitles_path = OUTPUT_DIR / f"{file_id}.srt"
    transcript_path = OUTPUT_DIR / f"{file_id}_transcript.txt"
    translation_path = OUTPUT_DIR / f"{file_id}_translation.txt"

    try:
        # 1. Extract audio from video
        extract_audio(video_path, audio_path)

        # 2. Convert speech to text
        transcript = transcribe_audio(audio_path)

        # 3. Translate transcript
        translated_text = translate_text(
            transcript,
            target_language,
        )

        # 4. Save transcript and translated text
        transcript_path.write_text(
            transcript,
            encoding="utf-8",
        )
        translation_path.write_text(
            translated_text,
            encoding="utf-8",
        )

        # 5. Generate dubbed speech
        synthesize_speech(
            translated_text,
            target_language,
            dubbed_audio_path,
        )

        # 6. Combine generated speech with video
        create_dubbed_video(
            video_path,
            dubbed_audio_path,
            output_video_path,
        )

        # 7. Generate subtitle file
        create_srt(
            translated_text,
            subtitles_path,
        )

        uploaded_videos[file_id]["status"] = "completed"
        uploaded_videos[file_id]["target_language"] = target_language

        return {
            "message": "Video dubbed successfully.",
            "file_id": file_id,
            "target_language": target_language,
            "transcript": transcript,
            "translated_text": translated_text,
            "video_url": f"/download/{file_id}",
            "subtitle_url": f"/subtitles/{file_id}",
            "status": "completed",
        }

    except HTTPException:
        raise
    except Exception as exc:
        uploaded_videos[file_id]["status"] = "failed"

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@app.get("/download/{file_id}")
def download_video(file_id: str):
    """Download the generated dubbed video."""
    output_video = OUTPUT_DIR / f"{file_id}_dubbed.mp4"

    if not output_video.exists():
        raise HTTPException(
            status_code=404,
            detail="Dubbed video is not ready. Run dubbing first.",
        )

    return FileResponse(
        path=str(output_video),
        media_type="video/mp4",
        filename="voxdub_dubbed.mp4",
    )


@app.get("/subtitles/{file_id}")
def download_subtitles(file_id: str):
    """Download the generated SRT subtitle file."""
    subtitle_path = OUTPUT_DIR / f"{file_id}.srt"

    if not subtitle_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Subtitles are not ready. Run dubbing first.",
        )

    return FileResponse(
        path=str(subtitle_path),
        media_type="application/x-subrip",
        filename="voxdub_subtitles.srt",
    )


@app.get("/transcript/{file_id}")
def get_transcript(file_id: str):
    """Get the original transcript and translated text."""
    transcript_path = OUTPUT_DIR / f"{file_id}_transcript.txt"
    translation_path = OUTPUT_DIR / f"{file_id}_translation.txt"

    if not transcript_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Transcript is not ready.",
        )

    return {
        "transcript": transcript_path.read_text(encoding="utf-8"),
        "translation": (
            translation_path.read_text(encoding="utf-8")
            if translation_path.exists()
            else ""
        ),
    }
