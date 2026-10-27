
import os
import base64
from pathlib import Path

from dotenv import load_dotenv
from sarvamai import SarvamAI

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

api_key = os.getenv("SARVAM_API_KEY")

if not api_key:
    raise ValueError("SARVAM_API_KEY not found in backend/.env")

client = SarvamAI(api_subscription_key=api_key)

text = "హలో! VoxDub AI కి స్వాగతం. ఇప్పుడు మనం తెలుగు వాయిస్ పరీక్షిస్తున్నాము."

response = client.text_to_speech.convert(
    text=text,
    language_code="te-IN",
    model="bulbul:v3",
    speaker="shreya",
)

audio_bytes = base64.b64decode(response.audios[0])
output_path = BASE_DIR / "telugu_test.wav"
output_path.write_bytes(audio_bytes)

print("Telugu voice generated successfully!")
print(f"Audio saved at: {output_path}")
