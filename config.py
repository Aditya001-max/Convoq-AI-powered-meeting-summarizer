import os
import tempfile
from dotenv import load_dotenv

load_dotenv()


def _fix_db_url(url: str) -> str:
    # Neon.tech and Heroku return postgres:// — SQLAlchemy 2.x requires postgresql://
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "convoq-change-me-in-production")
    SQLALCHEMY_DATABASE_URI = _fix_db_url(
        os.getenv("DATABASE_URL", "sqlite:///convoq.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Use /tmp on Vercel (read-only filesystem except /tmp); local uses system temp dir
    UPLOAD_FOLDER = os.getenv(
        "UPLOAD_FOLDER",
        os.path.join(tempfile.gettempdir(), "convoq_uploads"),
    )
    MAX_CONTENT_LENGTH = 64 * 1024 * 1024  # 64 MB
    AUDIO_EXTENSIONS = {"mp3", "mp4", "wav", "m4a", "webm", "ogg"}
    TEXT_EXTENSIONS = {"txt", "docx"}
    # Google Calendar OAuth2 (optional — needed for /calendar)
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
