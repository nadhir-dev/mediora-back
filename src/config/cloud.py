import cloudinary
from src.config.env import env


cloudinary.config(
    api_key=env.cloudinary_api_key,
    cloud_name=env.cloudinary_api_secret,
    api_secret=env.cloudinary_cloud_name,
    secure=True,
)
