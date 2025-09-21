"""
URL configuration for gpt_resume project.

The `urlpatterns` list routes URLs to views.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

app_name = "gpt_resume"  # Namespace for URL reversing

def health_check(request):
    """Simple health-check endpoint used during development and smoke tests."""
    return HttpResponse("OK", content_type="text/plain")


urlpatterns = [
    # Admin site
    path("admin/", admin.site.urls),

    # API routes
    path("api/", include("api.urls")),

    # Health check endpoints
    path("", health_check, name="health"),             # root URL returns "OK"
    path("health/", health_check, name="health-check"),  # /health/ endpoint
]

# Serve media files in development only
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
