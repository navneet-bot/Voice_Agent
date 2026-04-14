# Deployment Guide: Voice Agent Platform

This guide provides instructions for deploying the restructured Voice Agent Platform.

## 1. Project Structure

The project is now organized into two main directories:
- **`Frontend/`**: Contains the web interface (`index.html`).
- **`Backend/`**: Contains the FastAPI server, speech processing logic, and databases.

## 2. Local Deployment (Manual)

### Prerequisites
- Python 3.10+
- FFmpeg installed on your system (for audio processing)

### Setup Steps
1. **Navigate to the Backend directory**:
   ```bash
   cd Backend
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Update the `.env` file in the `Backend/` directory with your API keys:
   - `GROQ_API_KEY`
   - `ELEVENLABS_API_KEY` (if using ElevenLabs)
   - Other keys as required by your specific flows.

4. **Run the Server**:
   ```bash
   python server.py
   ```
   The server will start at `http://localhost:3000`.

5. **Access the Platform**:
   Open your browser and go to `http://localhost:3000`. The backend will automatically serve the frontend from the `Frontend/` directory.

## 3. Docker Deployment (Recommended)

### Prerequisites
- Docker and Docker Compose installed.

### Deploying with Docker Compose
1. **Build and Start**:
   From the project root directory (where `docker-compose.yml` is located):
   ```bash
   docker-compose up --build
   ```

2. **Access the Platform**:
   The application will be available at `http://localhost:3000`.

### Key Docker configurations:
- The **DB volume** is mapped to `./Backend/db` on your host machine to ensure data persistence.
- The **Environment variables** are passed through the `docker-compose.yml` or your system environment.

## 4. Troubleshooting
- **Frontend not loading**: Ensure the path in `Backend/server.py` correctly points to `../Frontend/index.html`.
- **Audio issues**: Ensure FFmpeg is installed and accessible in the system path or within the Docker container.
- **WebSocket Disconnection**: Check if the backend is running and the port 3000 is open and not blocked by a firewall.
