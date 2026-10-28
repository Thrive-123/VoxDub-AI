
# VoxDub AI — Multilingual Video Dubbing Platform

VoxDub AI is an AI-powered application designed to translate video speech into different languages and generate dubbed audio and subtitle files.

## Features

- Upload video files for processing
- Extract audio from videos using FFmpeg
- Convert speech into text using speech recognition
- Translate transcripts into supported target languages
- Generate dubbed audio using Sarvam AI text-to-speech
- Combine generated audio with the original video
- Generate and download subtitle files
- Access video processing functionality through REST APIs

## Tech Stack

**Frontend:** React.js, JavaScript, HTML, CSS

**Backend:** Python, FastAPI, REST APIs

**AI Services:** Sarvam AI, speech recognition, machine translation

**Media Processing:** FFmpeg

## Supported Languages

English, Hindi, Bengali, Tamil, Telugu, Kannada, Malayalam, Marathi, Gujarati, Punjabi, and Odia.

Language availability depends on the configured translation and speech-generation services.

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Thrive-123/VoxDub-AI.git
cd VoxDub-AI
```

### 2. Configure the backend

Navigate to the backend directory and install the required Python dependencies.

```bash
cd backend
pip install -r requirements.txt
```

Create a `.env` file in the backend directory:

```env
SARVAM_API_KEY=your_sarvam_api_key
```

Never commit your API key or `.env` file to GitHub.

### 3. Start the backend

```bash
uvicorn main:app --reload
```

The API should be available at:

http://127.0.0.1:8000

Interactive API documentation:

http://127.0.0.1:8000/docs

### 4. Start the frontend

Open a separate terminal and navigate to the frontend directory.

```bash
cd frontend
npm install
npm run dev
```

Open the local URL displayed by Vite in your terminal.

## Project Status

The project is under development. Features and supported languages may change as integration and testing continue.

## Future Enhancements

- Accurate timestamp-synchronized subtitles
- Improved audio-video synchronization
- Additional voice options and language support
- Cloud deployment and scalable media processing
- Improved error handling and performance

## Author

Chinthalacheruvu Thriveni

GitHub: https://github.com/Thrive-123
