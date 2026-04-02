import weaviate
from weaviate.auth import Auth

from app.core.config import settings

client = weaviate.connect_to_weaviate_cloud(
    cluster_url=settings.weaviate_url,
    auth_credentials=Auth.api_key(settings.weaviate_api_key),
)
