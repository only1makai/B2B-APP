import os
import secrets
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # SECRET_KEY must come from the environment in anything beyond local dev.
    # The fallback is random-per-process so a missing .env never means a
    # publicly-known signing key (sessions just reset on restart).
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'b2b.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")  # optional: app degrades to cache
    LOG_ENC_KEY = os.environ.get("LOG_ENC_KEY")        # Fernet key for interaction_log payloads

    # Outbound mail (verification links). Unset SMTP_HOST => mailer logs
    # messages instead of sending, so dev runs keyless.
    SMTP_HOST = os.environ.get("SMTP_HOST")
    SMTP_PORT = os.environ.get("SMTP_PORT", "587")
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
    MAIL_FROM = os.environ.get("MAIL_FROM", "no-reply@b2b.local")

    DEBUG = False


class DevConfig(Config):
    DEBUG = True


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # CSRF stays enabled: the test suite must prove POSTs fail without a token.
