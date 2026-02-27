import requests
from django.conf import settings
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible



class CemaStorage(Storage):

    def _upload(self, content):
        """
        Uploads the Django UploadedFile to the media service.
        """
        files = {
            "file": (
                content.name,                   
                content.file,                   
                getattr(content, "content_type", "application/octet-stream")
            )
        }

        resp = requests.post(
            f"{settings.MEDIA_STORAGE_URL}/upload/",
            headers={
                "X-App-Name": settings.MEDIA_APP_NAME,
                "X-App-Token": settings.MEDIA_APP_TOKEN,
            },
            files=files,
            stream=True,
            timeout=None 
        )

        resp.raise_for_status()
        return resp.json()["url"]

    def _save(self, name, content):
        print(f"[CemaStorage] _save called with name: {name}")
        return self._upload(content)

    def url(self, name):
        return name

    def exists(self, name):
        return False

    def delete(self, name):
        pass