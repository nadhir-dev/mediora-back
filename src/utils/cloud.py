from src.schemas.doctor_requests import RequestDocuments
import src.config.cloud
import cloudinary
import cloudinary.api


async def docs_exists_in_cloud(docs: RequestDocuments):
    pass
    ressource_metadata = cloudinary.api.resources(public_id="", ressource_type="")

    # check if format are coherent
