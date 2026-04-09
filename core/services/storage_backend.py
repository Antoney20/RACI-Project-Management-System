import requests
from urllib.parse import urlparse

from django.conf import settings
from django.core.files.storage import Storage


class CemaStorage(Storage):
    """
     Media storage backed by CEMA media service.

    DB stores:
        test/images/file.png

    URL generated from MEDIA_STORAGE_URL.
    """

    def __init__(self):
        self._base_url = getattr(settings, "MEDIA_STORAGE_URL", "").rstrip("/")
        self._app_name = getattr(settings, "MEDIA_APP_NAME", "")
        self._token = getattr(settings, "MEDIA_APP_TOKEN", "")
        self._validate_config()

    def _validate_config(self):
        missing = []

        if not self._base_url:
            missing.append("MEDIA_STORAGE_URL")

        if not self._app_name:
            missing.append("MEDIA_APP_NAME")

        if not self._token:
            missing.append("MEDIA_APP_TOKEN")

        if missing:
            raise ValueError(
                f"CemaStorage misconfigured. Missing: {', '.join(missing)}"
            )

    @property
    def _headers(self):
        return {
            "X-App-Name": self._app_name,
            "X-App-Token": self._token,
        }

    def _save(self, name, content):
        """
        Upload file and return OBJECT KEY to store in db
        """

        content_type = getattr(content, "content_type", None) or "application/octet-stream"

        if hasattr(content, "seek"):
            content.seek(0)

        try:
            resp = requests.post(
                f"{self._base_url}/upload/",
                headers=self._headers,
                files={"file": (name, content, content_type)},
                timeout=None,
            )
        except requests.ConnectionError:
            raise RuntimeError(
                f"CemaStorage cannot reach media service at {self._base_url}"
            )
            
        print("Status code:", resp.status_code)
        print("Response headers:", resp.headers)
        print("Response text:", resp.text)

        if resp.status_code == 403:
            raise PermissionError(
                "CemaStorage: invalid credentials or inactive app."
            )

        resp.raise_for_status()
        data = resp.json()
        file_url = data["url"]

        parsed = urlparse(file_url)
        path = parsed.path.lstrip("/")

        if path.startswith("media/"):
            path = path[len("media/"):]

        return path  # stored in DB

    def url(self, name):
        """
        Build public URL from object key.
        """
        if not name:
            return ""

        return f"{self._base_url.replace('/api', '')}/media/{name}"

    def exists(self, name):
        # filenames are already unique
        return False

    def delete(self, name):
        """
        Optional delete support.
        """
        try:
            requests.delete(
                f"{self._base_url}/files/",
                headers=self._headers,
                json={"path": name},
                timeout=30,
            )
        except Exception:
            pass

    def _open(self, name, mode="rb"):
        raise NotImplementedError(
            "CemaStorage does not support local file opening."
        )