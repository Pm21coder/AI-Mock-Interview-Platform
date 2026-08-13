# AI Mock Interview Platform

A full-stack mock interview platform with a Next.js frontend, Flask backend, MongoDB integration, Google Gemini AI, NLP analysis, and computer vision support.

## Tech stack

- Frontend: Next.js 16.3, React 19, Tailwind CSS
- Backend: Flask, Flask-SocketIO, PyMongo
- AI: Google Gemini API (google-genai SDK)
- Analysis: Optional OpenCV, MediaPipe, TextBlob, NLTK, scikit-learn (with local fallbacks)
- Database: MongoDB Atlas
- Payments: Razorpay
- Authentication: JWT

## Structure

- `frontend/` — Next.js application
- `backend/` — Flask API service
- `docker-compose.yml` — local container setup

## Quick start

### Backend

```bash
cd mock-interview-platform/backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

### Frontend

```bash
cd mock-interview-platform/frontend
npm install
npm run dev
```

Then open <http://localhost:3000>

## Environment variables

- Backend `.env` includes MongoDB and Gemini config
- Frontend `.env.local` includes `NEXT_PUBLIC_API_URL`

## Notes

This app is structured for a real interview workflow:

- generate questions
- record webcam answer
- analyze NLP and AI feedback
- review overall interview report

The initial build is intentionally resilient to missing external services by falling back to mock responses when API keys or services are unavailable.
