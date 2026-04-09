import threading
import requests
from urllib.parse import urlparse

from django.conf import settings
from django.core.files.storage import Storage

_request_local = threading.local()

def set_current_request(request):
    _request_local.request = request

def get_current_request():
    return getattr(_request_local, "request", None)


class CemaStorage(Storage):

    def __init__(self):
        self._base_url = getattr(settings, "MEDIA_STORAGE_URL", "").rstrip("/")
        if not self._base_url:
            raise ValueError("CemaStorage misconfigured. Missing: MEDIA_STORAGE_URL")

    @property
    def _headers(self):
        request = get_current_request()
        if request:
            app_name = request.headers.get("X-App-Name", "").strip()
            token = request.headers.get("X-App-Token", "").strip()
        else:
            # fallback to settings
            app_name = getattr(settings, "MEDIA_APP_NAME", "")
            token = getattr(settings, "MEDIA_APP_TOKEN", "")

        return {
            "X-App-Name": app_name,
            "X-App-Token": token,
        }

    def _save(self, name, content):
        headers = self._headers
        if not headers["X-App-Name"] or not headers["X-App-Token"]:
            raise PermissionError(
                "CemaStorage: no credentials found in request headers or settings."
            )

        content_type = getattr(content, "content_type", None) or "application/octet-stream"
        if hasattr(content, "seek"):
            content.seek(0)

        try:
            resp = requests.post(
                f"{self._base_url}/upload/",
                headers=headers,
                files={"file": (name, content, content_type)},
                timeout=None,
            )
        except requests.ConnectionError:
            raise RuntimeError(
                f"CemaStorage cannot reach media service at {self._base_url}"
            )

        if resp.status_code == 403:
            raise PermissionError("CemaStorage: invalid credentials or inactive app.")

        resp.raise_for_status()
        data = resp.json()

        parsed = urlparse(data["url"])
        path = parsed.path.lstrip("/")
        if path.startswith("media/"):
            path = path[len("media/"):]
        return path

    def url(self, name):
        if not name:
            return ""
        return f"{self._base_url.replace('/api', '')}/media/{name}"

    def exists(self, name):
        return False

    def delete(self, name):
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
        raise NotImplementedError("CemaStorage does not support local file opening.")