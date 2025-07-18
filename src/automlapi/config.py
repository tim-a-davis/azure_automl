from urllib.parse import quote_plus

from azure.identity import DefaultAzureCredential
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Azure AutoML settings - using environment variables
    azure_tenant_id: str | None = None
    azure_client_id: str | None = None
    azure_client_secret: str | None = None
    azure_subscription_id: str | None = None
    azure_ml_workspace: str | None = None
    azure_ml_resource_group: str | None = None

    # Azure SQL Database settings
    sql_server: str = "automldbserver.database.windows.net"
    sql_database: str = "automl"
    sql_port: int = 1433

    # Legacy SQL authentication (for local development only)
    sql_username: str = ""
    sql_password: str = ""

    # JWT settings
    jwt_secret: str | None = None

    # Environment setting
    environment: str = "production"

    # Azure credential for managed identity (lazy initialization)
    _azure_credential: DefaultAzureCredential | None = None

    def validate_required(self) -> None:
        # Skip Azure credential validation for local environment
        if self.environment == "local":
            # Only validate JWT secret for local testing
            if not self.jwt_secret:
                raise RuntimeError("Missing required setting: jwt_secret")
            return

        required = [
            "azure_tenant_id",
            "azure_client_id",
            "azure_client_secret",
            "azure_subscription_id",
            "azure_ml_workspace",
            "azure_ml_resource_group",
            "jwt_secret",
        ]
        missing = [r for r in required if not getattr(self, r)]
        if missing:
            raise RuntimeError(f"Missing required settings: {', '.join(missing)}")

    @property
    def database_url(self) -> str:
        """Build database URL for Azure SQL Database using Azure AD credentials."""

        # For local testing with SQLite (no database setup needed)
        if self.environment == "local":
            return "sqlite:///./automl_local.db"

        driver = "ODBC Driver 18 for SQL Server"

        if self.environment == "local" and self.sql_username and self.sql_password:
            # Local development with SQL authentication
            return (
                f"mssql+pyodbc://{self.sql_username}:{quote_plus(self.sql_password)}"
                f"@{self.sql_server}:{self.sql_port}/{self.sql_database}?driver={quote_plus(driver)}"
                "&Encrypt=yes&TrustServerCertificate=no"
            )

        # Azure AD Service Principal authentication using ODBC format
        return (
            f"mssql+pyodbc:///?odbc_connect="
            f"Driver={{ODBC Driver 18 for SQL Server}};"
            f"Server=tcp:{self.sql_server},{self.sql_port};"
            f"Database={self.sql_database};"
            f"Uid={self.azure_client_id};"
            f"Pwd={quote_plus(self.azure_client_secret)};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
            f"Authentication=ActiveDirectoryServicePrincipal"
        )

    @property
    def database_url_with_token(self) -> str:
        """Build database URL for Azure SQL Database using access token authentication.

        Use this when the service principal is part of a group that has admin access,
        but direct service principal authentication doesn't work.
        """
        # For local testing with SQLite (no database setup needed)
        if self.environment == "local":
            return "sqlite:///./automl_local.db"

        # Token-based authentication - requires getting token separately
        return (
            f"mssql+pyodbc:///?odbc_connect="
            f"Driver={{ODBC Driver 18 for SQL Server}};"
            f"Server=tcp:{self.sql_server},{self.sql_port};"
            f"Database={self.sql_database};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
            f"Authentication=ActiveDirectoryAccessToken"
        )

    def get_azure_credential(self) -> DefaultAzureCredential:
        """Get Azure Default Credential for token-based authentication."""
        if self._azure_credential is None:
            self._azure_credential = DefaultAzureCredential()
        return self._azure_credential

    async def get_database_access_token(self) -> str:
        """Get an access token for Azure SQL Database using DefaultAzureCredential."""
        credential = self.get_azure_credential()
        token = await credential.get_token("https://database.windows.net/.default")
        return token.token

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
settings.validate_required()
