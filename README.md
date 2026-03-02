# ZoKe Backend

FastAPI backend for the ZoKe mobile application, providing humor-as-a-service with reputation tracking (ZoScore) and community moderation.

## 🚀 Features
- **Humor Feed**: Personalised joke feed with Redis caching and background ingestion.
- **ZoScore**: Reputation system based on community "Funny" and "Not Funny" votes.
- **Engagement**: ReZoKe (commenting), sharing, and saving functionality.
- **Production Ready**: Configured for Render deployment with deep health checks and Supabase/Upstash integration.

## 🛠️ Tech Stack
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL (Supabase)
- **Cache**: Redis (Upstash)
- **Auth**: Firebase Authentication

## 🔧 Local Setup

1. **Clone the Repo**:
   ```bash
   git clone <repository-url>
   cd backend
   ```

2. **Setup Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Mac/Linux
   # or venv\Scripts\activate # Windows
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**:
   Create a `.env` file from the required variables below.

5. **Run Locally**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## 📡 Required Environment Variables
- `DATABASE_URL`: SQLAlchemy connection string (Supabase).
- `REDIS_URL`: Upstash Redis connection URL.
- `FIREBASE_CREDENTIALS_JSON`: Full content of your Firebase service account JSON.
- `SECRET_KEY`: Random string for security.

## 🌍 Deployment
- **Platform**: Render
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `bash start.sh`
- **Health Check Path**: `/health`
