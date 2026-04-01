import os


class Settings:
    app_name: str = "xariff"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./xariff.db")
    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    max_rows: int = int(os.getenv("MAX_ROWS", "500000"))
    max_cols: int = int(os.getenv("MAX_COLS", "50"))
    resend_api_key: str = os.getenv("RESEND_API_KEY", "")
    resend_api_base: str = os.getenv("RESEND_API_BASE", "https://api.resend.com")
    email_from: str = os.getenv("EMAIL_FROM", "Xariff <noreply@xariff.com>")
    email_reply_to: str = os.getenv("EMAIL_REPLY_TO", "contactus@xariff.com")
    contact_notification_to: str = os.getenv("CONTACT_NOTIFICATION_TO", "contactus@xariff.com")
    lead_notification_to: str = os.getenv("LEAD_NOTIFICATION_TO", "contactus@xariff.com")
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")


settings = Settings()
