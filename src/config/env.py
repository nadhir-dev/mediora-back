from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Env(BaseSettings):
    production: bool = Field(alias="PRODUCTION")

    db_url: str = Field(alias="DB_URL")
    redis_url: str = Field(alias="REDIS_URL")
    port: int = Field(alias="PORT")
    jwt_secret: str = Field(alias="JWT_SECRET")
    development_url: str = Field(alias="DEVELOPMENT_URL")
    production_url: str = Field(alias="PRODUCTION_URL")
    url: str = ""
    protocol: str = ""

    hash_secret: str = Field(alias="HASH_SECRET")

    mailtrap_username: str = Field(alias="MAILTRAP_USER")
    mailtrap_password: str = Field(alias="MAILTRAP_PASS")
    mailtrap_host: str = Field(alias="MAILTRAP_HOST")
    mailtrap_port: int = Field(alias="MAILTRAP_PORT")

    google_client_id: str = Field(alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(alias="GOOGLE_CLIENT_SECRET")
    google_redirect_url: str = Field(alias="GOOGLE_REDIRECT_URL")
    starlette_session_secret: str = Field(alias="STARLETTE_SESSION_SECRET")

    cloudinary_cloud_name: str = Field(alias="CLOUDINARY_CLOUD_NAME")
    cloudinary_api_key: str = Field(alias="CLOUDINARY_API_KEY")
    cloudinary_api_secret: str = Field(alias="CLOUDINARY_API_SECRET")

    spacemail_host: str = Field(alias="SPACEMAIL_HOST")
    spacemail_port: int = Field(alias="SPACEMAIL_PORT")
    spacemail_username: str = Field(alias="SPACEMAIL_USER")
    spacemail_password: str = Field(alias="SPACEMAIL_PASS")

    mail_sender: str = Field(alias="MAIL_SENDER")

    forever: int = Field(alias="FOREVER")
    creation_token_expiration: int = Field(alias="CREATION_TOKEN_EXPIRES")
    access_token_expiration: int = Field(alias="ACCESS_TOKEN_EXPIRES")
    refresh_token_expiration: int = Field(alias="REFRESH_TOKEN_EXPIRES")

    maximum_service_price: int = Field(alias="MAXIMUM_SERVICE_PRICE")

    chargily_secret_key: str = Field(alias="CHARGILY_SECRET_KEY")
    chargily_public_key: str = Field(alias="CHARGILY_PUBLIC_KEY")
    chargily_product_endpoint: str = Field(alias="CHARGILY_PRODUCT_ENDPOINT")
    chargily_price_endpoint: str = Field(alias="CHARGILY_PRICE_ENDPOINT")
    chargily_checkout_endpoint: str = Field(alias="CHARGILY_CHECKOUT_ENDPOINT")
    chargily_success_endpoint: str = Field(alias="CHARGILY_SUCCESS_ENDPOINT")

    resend_api_key: str = Field(alias="RESEND_API_KEY")

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="forbid")


env = Env()  # pyright: ignore[reportCallIssue]

production = env.production

setattr(env, "url", env.production_url if production else env.development_url)
setattr(env, "protocol", "https" if production else "http")
