from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    azure_tenant_id: str = "dummy"
    azure_client_id: str = "dummy"
    azure_client_secret: str = "dummy"
    azure_subscription_id: str = "dummy"
    azure_ml_workspace: str = "dummy"
    azure_ml_resource_group: str = "dummy"
    postgres_dsn: str = "dummy"
    jwt_secret: str = "dummy"

settings = Settings()
