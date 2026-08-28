from django_project.settings import BASE_DIR, DEBUG, env

# Uploads and collected static files live next to the code, not inside it.
CDN_DIR = BASE_DIR.parent

STATIC_URL = env("STATIC_URL")
MEDIA_URL = env("MEDIA_URL")
MEDIA_ROOT = CDN_DIR / env("MEDIA_ROOT")
STATIC_ROOT = CDN_DIR / env("STATIC_ROOT")

WHITENOISE_USE_FINDERS = DEBUG
