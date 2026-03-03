"""
Production settings for ERPro DZ.
All secrets come from environment variables — never hardcode here.
"""
from .base import *
from decouple import config

DEBUG = False

# Platform-injected public hostnames
RAILWAY_DOMAIN = config('RAILWAY_PUBLIC_DOMAIN', default='')
CUSTOM_DOMAIN   = config('CUSTOM_DOMAIN', default='')
RENDER_HOSTNAME = config('RENDER_EXTERNAL_HOSTNAME', default='')  # Render auto-injects this

# Support explicit ALLOWED_HOSTS env var (e.g. "*") — takes priority if set
_allowed_hosts_env = config('ALLOWED_HOSTS', default='')
if _allowed_hosts_env:
    ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts_env.split(',') if h.strip()]
else:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']
    for _host in [RAILWAY_DOMAIN, CUSTOM_DOMAIN, RENDER_HOSTNAME]:
        if _host:
            ALLOWED_HOSTS.append(_host)

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [o.strip() for o in config(
    'FRONTEND_URL', default='http://localhost:7474'
).split(',') if o.strip()]
CORS_ALLOW_CREDENTIALS = True

# ── SECURITY ──────────────────────────────────────────────────────────────────
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ── STATIC FILES (WhiteNoise) ─────────────────────────────────────────────────
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_URL = '/static/'

# ── LOGGING ──────────────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'apps': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}
