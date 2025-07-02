import os
from urllib.parse import quote_plus

from azure.identity import DefaultAzureCredential
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Azure AutoML settings - using environment variables
    azure_tenant_id: str
    azure_client_id: str
    azure_client_secret: str
    azure_subscription_id: str
    azure_ml_workspace: str
    azure_ml_resource_group: str

    # Azure SQL Database settings
    sql_server: str = "automldbserver.database.windows.net"
    sql_database: str = "automldb"
    sql_port: int = 1433

    # For local development only (optional)
    sql_username: str = ""
    sql_password: str = ""

    # JWT settings
    jwt_secret: str

    # Azure credential for managed identity
    _azure_credential: DefaultAzureCredential = DefaultAzureCredential()

    @property
    def database_url(self) -> str:
        """Build database URL for Azure SQL Database with managed identity"""
        driver = "ODBC Driver 18 for SQL Server"

        if (
            os.getenv("ENVIRONMENT") == "local"
            and self.sql_username
            and self.sql_password
        ):
            # Local development with SQL authentication
            return f"mssql+pyodbc://{self.sql_username}:{quote_plus(self.sql_password)}@{self.sql_server}:{self.sql_port}/{self.sql_database}?driver={quote_plus(driver)}&Encrypt=yes&TrustServerCertificate=no"

        # Azure deployment with managed identity (no password needed)
        return f"mssql+pyodbc://@{self.sql_server}:{self.sql_port}/{self.sql_database}?driver={quote_plus(driver)}&Authentication=ActiveDirectoryDefault&Encrypt=yes&TrustServerCertificate=no"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
