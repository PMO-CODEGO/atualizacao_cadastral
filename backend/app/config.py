from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mysql_host: str = "db"
    mysql_port: int = 3306
    mysql_database: str = "atualizacao_cadastral"
    mysql_user: str = "codego_app"
    mysql_password: str = "change_me"

    app_env: str = "development"
    app_secret_key: str = "change_me_secret"

    upload_dir: str = "/app/storage/uploads"
    max_upload_size_mb: int = 10

    protocol_prefix: str = "ATC"

    # E-mail fixo da empresa que recebe TODAS as solicitações de atualização cadastral
    notification_email: str = ""

    # E-mail — provider "smtp" (Gmail, Brevo, etc.) ou "outlook_graph" (Microsoft Graph, para Outlook/Hotmail)
    email_provider: str = "smtp"

    # E-mail (SMTP)
    smtp_host: str = "smtp-relay.brevo.com"
    smtp_port: int = 587
    smtp_use_tls: bool = True
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "Sistema de Atualização Cadastral CODEGO"
    smtp_enabled: bool = False

    # Outlook via Microsoft Graph (OAuth2)
    outlook_client_id: str = ""
    outlook_tenant: str = "consumers"
    outlook_sender_email: str = ""
    outlook_token_cache_path: str = "/app/storage/outlook_token_cache.bin"

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )


settings = Settings()
