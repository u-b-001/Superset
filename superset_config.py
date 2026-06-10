import os

SUPERSET_ENV = os.environ.get("SUPERSET_ENV", "development").lower()
IS_PRODUCTION = SUPERSET_ENV in {"prod", "production"}
EMBEDDED_PORTAL_ORIGIN = os.environ.get(
    "EMBEDDED_PORTAL_ORIGIN",
    "https://ga.samarthx.du.ac.in",
)

ROW_LIMIT = 5000

# Hide the "Development" environment tag in the navbar
ENVIRONMENT_TAG_CONFIG = {
    "variable": "SUPERSET_ENV",
    "values": {
        "development": {
            "color": "",
            "text": "",  # Empty text hides the tag
        },
        "production": {
            "color": "",
            "text": "",
        },
    },
}

# Flask App Builder configuration
SECRET_KEY = os.environ.get('SUPERSET_SECRET_KEY', 'CHANGE_ME_IN_ENV')

# Allow localhost requests
ENABLE_PROXY_FIX = True
SESSION_COOKIE_SAMESITE = "None" if IS_PRODUCTION else "Lax"
SESSION_COOKIE_SECURE = IS_PRODUCTION
SESSION_COOKIE_DOMAIN = None

# Database connection — reads from DATABASE_URI env var
SQLALCHEMY_DATABASE_URI = os.environ.get(
    'DATABASE_URI',
    'postgresql+psycopg2://superset_user:CHANGE_ME@localhost:5432/superset'
)

# Flask-WTF CSRF
WTF_CSRF_ENABLED = IS_PRODUCTION
WTF_CSRF_EXEMPT_LIST = []
WTF_CSRF_TIME_LIMIT = 60 * 60 * 24 * 365

# Mapbox
MAPBOX_API_KEY = ''

# Branding
APP_NAME = "SamarthX Dashboards"
APP_ICON = "/static/assets/images/samarthx_logo.png"
LOGO_TARGET_PATH = '/'
LOGO_TOOLTIP = "SamarthX LOGO"
LOGO_RIGHT_TEXT = "Dashboards"
FAVICONS = [{"href": "/static/assets/images/SXfavicon.svg"}]

# ── Embedded Dashboard SDK ──
FEATURE_FLAGS = {
    "EMBEDDED_SUPERSET": True,
    "DASHBOARD_NATIVE_FILTERS": True,
    "DASHBOARD_CROSS_FILTERS": True,
    "ENABLE_TEMPLATE_PROCESSING": True,
    "ALERT_REPORTS": True,
    "DYNAMIC_PLUGINS": False,
}

# Enable all visualization types (don't block any)
VIZ_TYPE_DENYLIST = []

# Role assigned to guest/embedded users
GUEST_ROLE_NAME = "Public"

# Secret used to sign guest tokens (change this in production!)
GUEST_TOKEN_JWT_SECRET = os.environ.get(
    'GUEST_TOKEN_JWT_SECRET',
    'CHANGE_ME_IN_ENV'
)

# CORS — allow your portal's domain to embed dashboards
CORS_OPTIONS = {
    "supports_credentials": True,
    "allow_headers": ["*"],
    "resources": ["*"],
    "origins": [EMBEDDED_PORTAL_ORIGIN]
    if IS_PRODUCTION
    else [
        "http://localhost:3777",  # your portal dev server
        "http://localhost:8080",  # alternate local portal URL
    ],
}

# Keep local embedding easy, but enforce security headers in production.
if IS_PRODUCTION:
    TALISMAN_ENABLED = True
    TALISMAN_CONFIG = {
        "force_https": True,
        "strict_transport_security": True,
        "strict_transport_security_max_age": 31536000,
        "frame_options": None,
        "content_security_policy": {
            "default-src": ["'self'"],
            "img-src": ["'self'", "data:", "blob:", "https:"],
            "font-src": ["'self'", "data:", "https:"],
            "style-src": ["'self'", "'unsafe-inline'", "https:"],
            "script-src": ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
            "connect-src": ["'self'", "https:"],
            "worker-src": ["'self'", "blob:"],
            "frame-ancestors": [
                "'self'",
                EMBEDDED_PORTAL_ORIGIN,
            ],
        },
    }
else:
    # Disable Talisman for local dev (it blocks iframes without CSP tuning)
    TALISMAN_ENABLED = False
    CONTENT_SECURITY_POLICY_WARNING = False


# ── SamarthX eGov Color Scheme ──────────────────────────────────────────────
EXTRA_CATEGORICAL_COLOR_SCHEMES = [
    {
        "id": "samarthx_egov",
        "description": "SamarthX eGov official color palette",
        "label": "SamarthX eGov",
        "isDefault": True,
        "colors": [
            "#2563eb",  # Bright blue (primary)
            "#f5a623",  # Orange accent (SamarthX X logo)
            "#1a3fbb",  # Royal blue
            "#38bdf8",  # Sky blue
            "#fb923c",  # Light orange
            "#0a1f6e",  # Dark navy
            "#7dd3fc",  # Pale blue
            "#fbbf24",  # Amber
            "#1d4ed8",  # Medium blue
            "#fed7aa",  # Peach
        ],
    }
]

# Make SamarthX eGov the default color scheme for all charts
DEFAULT_VIZ_TYPE = "table"
EXTRA_SEQUENTIAL_COLOR_SCHEMES = [
    {
        "id": "samarthx_sequential",
        "description": "SamarthX blue sequential palette",
        "label": "SamarthX Blue",
        "isDiverging": False,
        "colorScheme": [
            "#e8f0fe",
            "#c7d9fc",
            "#93b8f9",
            "#5a8ef0",
            "#2563eb",
            "#1a3fbb",
            "#0a1f6e",
        ],
    }
]

# ── Chart border radius via OVERRIDE_CSS ─────────────────────────────────────
# Adds rounded corners to ECharts canvas wrappers and all chart containers
OVERRIDE_CSS = """
    /* Rounded chart containers */
    .chart-container,
    .slice_container,
    .chart-slice,
    .echarts-for-react,
    .slice__description,
    .dashboard-chart {
        border-radius: 12px !important;
        overflow: hidden !important;
    }

    /* ECharts tooltip — rounded and branded */
    .echarts-tooltip,
    div[class*="tooltip"] {
        border-radius: 10px !important;
        border: 1px solid #d6e0f5 !important;
        box-shadow: 0 4px 16px rgba(10, 31, 110, 0.15) !important;
        font-family: 'DM Sans', sans-serif !important;
    }

    /* Table chart rounded header */
    .dt-bootstrap4 thead th:first-child { border-radius: 10px 0 0 0 !important; }
    .dt-bootstrap4 thead th:last-child  { border-radius: 0 10px 0 0 !important; }
    .dt-bootstrap4 thead th {
        background-color: #1a3fbb !important;
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    .dt-bootstrap4 tbody tr:nth-child(even) td {
        background-color: #f0f4ff !important;
    }
    .dt-bootstrap4 tbody tr:hover td {
        background-color: #dce7fb !important;
    }

    /* Big Number KPI */
    .big-number .header-line {
        color: #1a3fbb !important;
        font-weight: 700 !important;
    }
    .big-number .subheader-line {
        color: #2563eb !important;
    }
"""
