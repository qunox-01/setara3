import os


class Settings:
    app_name: str = "xariff"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./xariff.db")
    max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    max_rows: int = int(os.getenv("MAX_ROWS", "500000"))
    max_cols: int = int(os.getenv("MAX_COLS", "50"))


settings = Settings()
