
import os
from pathlib import Path

from dotenv import load_dotenv
from sarvamai import SarvamAI

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

api_key = os.getenv("SARVAM_API_KEY")

if not api_key:
    raise ValueError(
        "SARVAM_API_KEY not found. Check the backend/.env file."
    )

client = SarvamAI(api_subscription_key=api_key)

response = client.text.translate(
    input="Hello, welcome to VoxDub AI.",
    source_language_code="en-IN",
    target_language_code="te-IN",
    model="sarvam-translate:v1",
)

print("Translation successful!")
print("Detected source:", response.source_language_code)
print("Telugu text:", response.translated_text)
