"""
Application settings using pydantic-settings.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_name: str = "crm_interactions_db"
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_host: str = "db"
    db_port: int = 5432
    db_pool_size: int = 10
    db_max_overflow: int = 20
    app_env: str = "local"
    app_port: int = 8002
    log_level: str = "INFO"

    # AWS S3
    s3_bucket: str = ""
    s3_region: str = "us-east-1"
    s3_endpoint_url: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
