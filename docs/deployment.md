# Deployment

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `GROQ_API_KEY` | Yes | Groq Cloud LLM access |
| `DEEPGRAM_API_KEY` | For Deepgram STT | Deepgram Nova-2 transcription |
| `CARTESIA_API_KEY` | For Cartesia TTS | Cartesia Sonic voice synthesis |
| `TWILIO_ACCOUNT_SID` | For Twilio | Twilio API auth |
| `TWILIO_AUTH_TOKEN` | For Twilio | Twilio API auth |
| `PLATFORM_API_KEY` | Optional | Dashboard write-action auth (X-API-Key header) |
| `PLATFORM_FEATURE_PROFILE` | Optional | `live` (all on) or `shadow` (all off) |
| `NEXT_PUBLIC_API_URL` | Frontend | Backend URL (default: localhost:8000) |

## Local Development

### Prerequisites
- Python 3.10+
- Node.js 18+
- FFmpeg

### Backend
```bash
cd Backend
pip install -r requirements.txt
python main.py
# API at http://localhost:8000
```

### Frontend
```bash
cd frontend-next
npm install
npm run dev
# Dashboard at http://localhost:3000
```

## Docker Deployment

### Dockerfile
```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg espeak-ng build-essential
WORKDIR /app/Backend
COPY Backend/requirements.txt .
RUN pip install -r requirements.txt
COPY . /app/
EXPOSE 3000
CMD ["python", "main.py"]
```

### docker-compose.yml
```yaml
services:
  voice-agent-platform:
    build: .
    ports:
      - "3000:3000"
    volumes:
      - ./Backend/db:/app/Backend/db
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
    restart: always
```

### Run
```bash
docker-compose up --build
```

## Railway Deployment

### railway.json
```json
{
  "build": { "builder": "NIXPACKS" },
  "deploy": {
    "startCommand": "bash -c 'cd /app/Backend && PYTHONPATH=. gunicorn main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT'"
  }
}
```

### Procfile
```
web: bash -c "cd /app/Backend && PYTHONPATH=. gunicorn main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT"
```

## Production Server

```bash
cd Backend
python start_production.py
```
- Uses Gunicorn with UvicornWorker
- 4 workers
- Configurable port and log level

## Production Checklist

1. Set all required environment variables
2. Enable HTTPS (required for browser microphone access)
3. Configure Nginx WebSocket proxy headers:
   ```nginx
   location /ws/ {
       proxy_pass http://localhost:8000;
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";
   }
   ```
4. Set `PLATFORM_FEATURE_PROFILE=live` for full feature set
5. Mount `Backend/db` as a persistent volume
6. Verify health endpoint: `GET /health` returns 200

## Rollback

Revert to shadow mode with a single env change:
```
PLATFORM_FEATURE_PROFILE=shadow
```
This disables all new platform features. Individual `FEATURE_*` flags still work for fine-grained control.
