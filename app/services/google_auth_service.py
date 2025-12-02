from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
import os

config = Config(".env")
oauth = OAuth(config)

google_oauth = oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)
