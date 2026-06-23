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
    'postgresql+psycopg2://superset_user:password@localhost:5432/superset'
)

# Flask-WTF CSRF
WTF_CSRF_ENABLED = IS_PRODUCTION
WTF_CSRF_EXEMPT_LIST = ['/api/ai-chat']
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

# Ant Design Theme branding overrides (forces the React navbar logo to update)
THEME_DEFAULT = {
    "algorithm": "default",
    "token": {
        "brandLogoUrl": "/static/assets/images/samarthx_logo.png",
        "brandLogoAlt": "SamarthX Dashboards",
    }
}
THEME_DARK = {
    "algorithm": "dark",
    "token": {
        "brandLogoUrl": "/static/assets/images/samarthx_logo.png",
        "brandLogoAlt": "SamarthX Dashboards",
    }
}


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

    /* Table chart rounded header and adaptive borders/backgrounds */
    thead th:first-child,
    .table thead th:first-child,
    .dt-bootstrap4 thead th:first-child { border-radius: 10px 0 0 0 !important; }
    
    thead th:last-child,
    .table thead th:last-child,
    .dt-bootstrap4 thead th:last-child  { border-radius: 0 10px 0 0 !important; }
    
    thead th,
    .table thead th,
    .dt-bootstrap4 thead th {
        background-color: #1a3fbb !important;
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    
    /* Enforce inherit color on all cells to adapt correctly in dark mode */
    tbody tr td,
    .table tbody tr td,
    .dt-bootstrap4 tbody tr td {
        color: inherit !important;
    }
    
    /* Zebra Striping using 5% opacity blue (harmonious and adaptive in both light and dark modes) */
    tbody tr:nth-child(even) td,
    .table tbody tr:nth-child(even) td,
    .dt-bootstrap4 tbody tr:nth-child(even) td {
        background-color: rgba(37, 99, 235, 0.05) !important;
    }
    
    /* Hover highlighting using 12% opacity blue */
    tbody tr:hover td,
    .table tbody tr:hover td,
    .dt-bootstrap4 tbody tr:hover td {
        background-color: rgba(37, 99, 235, 0.12) !important;
    }

    /* Input controls (search field and page length select box) */
    .dataTables_wrapper select,
    .dataTables_wrapper input {
        background-color: rgba(37, 99, 235, 0.05) !important;
        color: inherit !important;
        border: 1px solid rgba(37, 99, 235, 0.2) !important;
        border-radius: 6px !important;
        padding: 4px 8px !important;
        outline: none !important;
    }
    
    .dataTables_wrapper select option {
        background-color: #ffffff !important;
        color: #000000 !important; /* ensures options are readable in dropdown menus */
    }

    /* DataTables Pagination buttons styling */
    .pagination .page-item .page-link {
        background-color: transparent !important;
        color: inherit !important;
        border: 1px solid rgba(37, 99, 235, 0.15) !important;
        border-radius: 4px !important;
        margin: 0 2px !important;
    }
    .pagination .page-item.active .page-link {
        background-color: #2563eb !important;
        color: #ffffff !important;
        border-color: #2563eb !important;
    }
    .pagination .page-item.disabled .page-link {
        opacity: 0.5 !important;
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

def ensure_n8n_running():
    import socket
    import subprocess
    import time

    # Check if port 5678 is already active
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            # If connect_ex returns 0, the port is open and n8n is running
            if s.connect_ex(('127.0.0.1', 5678)) == 0:
                return
        except Exception:
            pass

    # Start n8n in a separate background process
    env = os.environ.copy()
    env['NODE_OPTIONS'] = '--max-old-space-size=4096'
    
    try:
        creationflags = 0
        if os.name == 'nt':
            # On Windows, launch n8n in a new console window so it does not block/clutter the main Superset console
            creationflags = subprocess.CREATE_NEW_CONSOLE
            subprocess.Popen(['n8n', 'start'], env=env, shell=True, creationflags=creationflags)
        else:
            # On Linux/macOS, run in background and detach
            with open(os.devnull, 'wb') as devnull:
                subprocess.Popen(['n8n', 'start'], env=env, stdout=devnull, stderr=devnull, start_new_session=True)
        
        # Wait up to 10 seconds for n8n to start listening
        for _ in range(20):
            time.sleep(0.5)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.2)
                try:
                    if s.connect_ex(('127.0.0.1', 5678)) == 0:
                        # Give n8n a brief moment to register internal webhook routes after port opens
                        time.sleep(5.0)
                        break
                except Exception:
                    pass
    except Exception:
        # Gracefully handle situations where n8n is not installed locally
        pass

def FLASK_APP_MUTATOR(app):
    ensure_n8n_running()
    from flask import request, Response
    import requests
    from superset.extensions import csrf

    @app.route('/api/ai-chat', methods=['POST'])
    def ai_chat_proxy():
        ensure_n8n_running()
        try:
            n8n_url = os.environ.get('N8N_WEBHOOK_URL', 'http://127.0.0.1:5678/webhook/ai-chat')
            resp = requests.post(
                n8n_url,
                json=request.json,
                headers={'Content-Type': 'application/json'},
                timeout=600
            )
            
            # If the production webhook is not active, try falling back to the test webhook
            if resp.status_code == 404 and b"not registered" in resp.content:
                test_url = n8n_url.replace('/webhook/', '/webhook-test/')
                try:
                    test_resp = requests.post(
                        test_url,
                        json=request.json,
                        headers={'Content-Type': 'application/json'},
                        timeout=600
                    )
                    # If test webhook succeeded or returned a non-404, use its response
                    if test_resp.status_code != 404:
                        resp = test_resp
                except Exception:
                    pass

            # If n8n returns 404 (workflow inactive / not testing)
            if resp.status_code == 404:
                import json
                error_response = json.dumps({
                    "answer": "The AI Chat workflow is loaded in n8n, but it is currently inactive. "
                              "Please open n8n (http://localhost:5678), open the 'SamarthX AI Chat' workflow, "
                              "and toggle the 'Active' switch in the top-right corner to ON."
                })
                return Response(error_response, status=200, headers={'Content-Type': 'application/json'})

            response = Response(
                resp.content,
                status=resp.status_code,
                headers={'Content-Type': 'application/json'}
            )
            return response
        except Exception as e:
            import json
            error_response = json.dumps({"answer": f"Could not reach the AI service. Make sure n8n is running on port 5678. (Details: {str(e)})"})
            return Response(error_response, status=502, headers={'Content-Type': 'application/json'})

    csrf.exempt(ai_chat_proxy)

