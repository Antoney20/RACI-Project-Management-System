from core.services.storage_backend import set_current_request

class CemaStorageRequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_request(request)
        response = self.get_response(request)
        set_current_request(None)  # clear after request
        return response