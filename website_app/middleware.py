# Create a new file: website_app/middleware.py
from django.core.files.storage import default_storage


class StorageDebugMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Print this during server startup
        print(f"\n\n==== STORAGE CONFIGURATION ====")
        print(f"Default storage class: {default_storage.__class__.__name__}")
        print(f"==== END STORAGE CONFIG ====\n\n")

    def __call__(self, request):
        return self.get_response(request)
