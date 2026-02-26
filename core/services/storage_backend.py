import requests
from django.conf import settings
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class CemaStorage(Storage):

    def _upload(self, file):
        print(f"[CemaStorage] Uploading to {settings.MEDIA_STORAGE_URL}/files/upload/")
        print(f"[CemaStorage] App: {settings.MEDIA_APP_NAME}")
        print(f"[CemaStorage] Token set: {bool(settings.MEDIA_APP_TOKEN)}")

        resp = requests.post(
            f"{settings.MEDIA_STORAGE_URL}/files/upload/",
            headers={
                "X-App-Name": settings.MEDIA_APP_NAME,
                "X-App-Token": settings.MEDIA_APP_TOKEN,
            },
            files={"file": file},
            timeout=30,
        )

        print(f"[CemaStorage] Response status: {resp.status_code}")
        print(f"[CemaStorage] Response body: {resp.text}")

        resp.raise_for_status()
        url = resp.json()["url"]
        print(f"[CemaStorage] Saved at: {url}")
        return url

    def _save(self, name, content):
        print(f"[CemaStorage] _save called with name: {name}")
        return self._upload(content)

    def url(self, name):
        return name

    def exists(self, name):
        return False

    def delete(self, name):
        pass