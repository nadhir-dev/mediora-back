# authlib, httpx, itsdangerous
from authlib.integrations.starlette_client import OAuth

from src.config.env import env


oauth = OAuth()
oauth.register(
    name="google",
    client_id=env.google_client_id,
    client_secret=env.google_client_secret,
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    authorize_params={"scope": "openid email profile"},
    access_token_url="https://oauth2.googleapis.com/token",
    client_kwargs={"scope": "openid email profile"},
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    #   response_type: code is implicit here
)
