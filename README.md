# Care.AI - Clinical Appointment Booking Voice Agent

Care.AI is a production-ready, low-latency (<450ms) real-time multilingual voice AI agent designed for clinical appointment booking. It supports English, Hindi, and Tamil with automatic language detection.

## 🚀 Features

- **Real-Time Voice Interaction**: Low-latency WebSocket-based audio streaming.
- **Multilingual Support**: Automatic detection and response in English, Hindi, and Tamil.
- **Appointment Management**: Book, cancel, reschedule, and check doctor availability.
- **Contextual Memory**: Redis for session memory and PostgreSQL for persistent data.
- **Low Latency**: Optimized pipeline (STT -> LLM -> TTS) targeting < 450ms response time.

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python)
- **STT**: Faster-Whisper
- **LLM**: OpenAI GPT-3.5/4
- **TTS**: gTTS (Google Text-to-Speech)
- **Database**: PostgreSQL
- **Memory**: Redis
- **Language Detection**: langdetect

## 📋 Prerequisites

Ensure you have the following installed locally:
- Python 3.9+
- PostgreSQL
- Redis
- FFmpeg (required for audio processing)

## ⚙️ Local Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd care.ai/backend
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Create a `.env` file in the `backend` directory:
   ```env
   PORT=8000
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/careai
   REDIS_URL=redis://localhost:6379/0
   OPENAI_API_KEY=your_openai_api_key_here
   OPENAI_MODEL=gpt-3.5-turbo
   ```

5. **Initialize Database**:
   Make sure PostgreSQL is running and you have created a database named `careai`.
   ```bash
   python seed.py
   ```

6. **Run the Application**:
   ```bash
   uvicorn app.main:app --reload
   ```

## 🏗️ Architecture

1. **WebSocket**: Receives raw audio bytes from the client.
2. **STT (Faster-Whisper)**: Converts audio to text in ~120ms.
3. **Language Detection**: Identifies if the user is speaking English, Hindi, or Tamil.
4. **LLM Agent (OpenAI)**: Processes intent, extracts entities (doctor, date, time), and decides on tool calls.
5. **Tool Execution**: Interacts with PostgreSQL to manage appointments.
6. **Memory**:
   - **Redis**: Stores conversation history and session context.
   - **PostgreSQL**: Stores persistent user, doctor, and appointment data.
7. **TTS (gTTS)**: Generates response audio in ~100ms.
8. **Streaming**: Sends audio bytes back to the client via WebSocket.

## ⚡ Latency Breakdown (Targets)

- **STT**: ~120ms (using Faster-Whisper with int8 quantization)
- **LLM**: ~200ms (using GPT-3.5-turbo)
- **TTS**: ~100ms (using gTTS/ElevenLabs)
- **Total Overhead**: < 30ms
- **Total Target**: < 450ms

## 🛑 Error Handling

- **LLM Failures**: Fallback to predefined multilingual responses.
- **Scheduling Conflicts**: Suggests alternative slots if a booking conflict occurs.
- **Network Issues**: Graceful WebSocket disconnection handling.

## 🧪 Testing

You can test the WebSocket endpoint using a tool like `wscat` or a custom client script:
```bash
wscat -c ws://localhost:8000/api/v1/ws/voice
```
(Note: You'll need to send audio bytes in the expected format for the STT to process it).
