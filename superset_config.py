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

# CORS — allow origins for API, chat widget, and embedding dashboards
ENABLE_CORS = True
CORS_OPTIONS = {
    "supports_credentials": True,
    "allow_headers": ["*"],
    "resources": ["*"],
    "methods": ["GET", "HEAD", "POST", "OPTIONS", "PUT", "DELETE"],
    "origins": [EMBEDDED_PORTAL_ORIGIN]
    if IS_PRODUCTION
    else [
        "http://localhost:3777",
        "http://localhost:8080",
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:8088",
        "http://127.0.0.1:8088",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5678",
        "http://127.0.0.1:5678",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
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
    try:
        from ai_integration.service_manager import ensure_n8n_running as _ensure_n8n
        _ensure_n8n(timeout=35.0)
    except Exception:
        try:
            import sys
            from pathlib import Path
            ai_dir = str(Path(__file__).parent / "ai_integration")
            if ai_dir not in sys.path:
                sys.path.insert(0, ai_dir)
            from service_manager import ensure_n8n_running as _ensure_n8n
            _ensure_n8n(timeout=35.0)
        except Exception:
            pass

def ensure_ai_services_running():
    try:
        from ai_integration.service_manager import ensure_all_services
        ensure_all_services(wait_for_ready=False)
    except Exception:
        try:
            import sys
            from pathlib import Path
            ai_dir = str(Path(__file__).parent / "ai_integration")
            if ai_dir not in sys.path:
                sys.path.insert(0, ai_dir)
            from service_manager import ensure_all_services
            ensure_all_services(wait_for_ready=False)
        except Exception:
            pass

def ensure_websocket_server_running():
    ensure_ai_services_running()


def FLASK_APP_MUTATOR(app):
    ensure_ai_services_running()
    import time
    import json
    import requests
    from flask import request, Response  # type: ignore
    from superset.extensions import csrf  # type: ignore

    @app.after_request
    def add_ai_cors_headers(response):
        if request.path.startswith('/api/ai-chat'):
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, X-CSRFToken, *'
            response.headers['Access-Control-Max-Age'] = '86400'
        return response

    @app.route('/api/ai-chat', methods=['GET', 'POST', 'OPTIONS'])
    def ai_chat_proxy():
        cors_headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With, X-CSRFToken, *',
            'Access-Control-Max-Age': '86400',
        }

        if request.method == 'OPTIONS':
            return Response('', status=200, headers=cors_headers)

        if request.method == 'GET':
            return Response(
                json.dumps({"status": "healthy", "service": "SamarthX AI Chat Proxy"}),
                status=200,
                headers={'Content-Type': 'application/json', **cors_headers}
            )

        start_time = time.time()
        guard_info = {
            "status": "SAFE",
            "allowed": True,
            "model": "gemma2:2b (Ollama)",
            "check_type": "ollama_slm",
            "latency_ms": 0.0
        }
        try:
            req_data = request.get_json(silent=True) or {}
            question = req_data.get('question', '')
            print("\n" + "=" * 70, flush=True)
            print(f"[SamarthX AI Chat] Incoming Question: \"{question}\"", flush=True)
            print("=" * 70, flush=True)

            # ── Open-Source SLM Input Guardrail (Ollama) ──
            try:
                try:
                    from ai_integration.guardrails import guardrail  # type: ignore
                except ImportError:
                    import sys
                    from pathlib import Path
                    ai_int_path = str(Path(__file__).parent / "ai_integration")
                    if ai_int_path not in sys.path:
                        sys.path.insert(0, ai_int_path)
                    from guardrails import guardrail  # type: ignore

                guard_result = guardrail.evaluate(question)
                guard_info = guard_result.to_dict()

                print(f"[Ollama Guardrail] Status: {guard_info.get('status')} | Model: {guard_info.get('model')} | Latency: {guard_info.get('latency_ms')}ms", flush=True)
                if not guard_result.is_allowed:
                    print(f"[Ollama Guardrail] 🔴 BLOCKED! Reason: {guard_result.reason} (Category: {guard_result.category})", flush=True)
                    print("=" * 70 + "\n", flush=True)
                    return Response(
                        json.dumps({
                            "answer": guard_result.message,
                            "guardrail_blocked": True,
                            "category": guard_result.category,
                            "guardrail": guard_info
                        }),
                        status=200,
                        headers={'Content-Type': 'application/json', **cors_headers}
                    )
            except Exception as ge:
                import logging
                logging.getLogger("superset").warning(f"Guardrail evaluation error: {ge}")

            ensure_n8n_running()

            n8n_url = os.environ.get('N8N_WEBHOOK_URL', 'http://127.0.0.1:5678/webhook/ai-chat')
            resp = None
            for req_attempt in range(3):
                try:
                    resp = requests.post(
                        n8n_url,
                        json=req_data,
                        headers={'Content-Type': 'application/json'},
                        timeout=600
                    )
                    break
                except requests.exceptions.RequestException as re:
                    if req_attempt < 2:
                        time.sleep(1.5)
                    else:
                        raise re

            if resp is None:
                error_response = json.dumps({
                    "answer": "Could not reach the AI service. Make sure n8n is running on port 5678.",
                    "guardrail": guard_info
                })
                return Response(error_response, status=503, headers={'Content-Type': 'application/json', **cors_headers})

            # If the production webhook is not active, try falling back to the test webhook
            if resp.status_code == 404 and resp.content and b"not registered" in resp.content:
                test_url = n8n_url.replace('/webhook/', '/webhook-test/')
                try:
                    test_resp = requests.post(
                        test_url,
                        json=req_data,
                        headers={'Content-Type': 'application/json'},
                        timeout=600
                    )
                    if test_resp is not None and test_resp.status_code != 404:
                        resp = test_resp
                except Exception:
                    pass

            if resp.status_code == 404:
                error_response = json.dumps({
                    "answer": "The AI Chat workflow is loaded in n8n, but it is currently inactive. "
                              "Please open n8n (http://localhost:5678), open the 'SamarthX AI Chat' workflow, "
                              "and toggle the 'Active' switch in the top-right corner to ON.",
                    "guardrail": guard_info
                })
                return Response(error_response, status=200, headers={'Content-Type': 'application/json', **cors_headers})

            total_latency = round((time.time() - start_time) * 1000, 1)
            
            # Parse and enrich response
            resp_content = resp.content.decode('utf-8', errors='ignore')
            resp_json = {}
            try:
                resp_json = json.loads(resp_content)
            except Exception:
                resp_json = {"answer": resp_content}

            resp_json["guardrail"] = guard_info
            resp_json["total_latency_ms"] = total_latency

            answer_text = resp_json.get("answer", "")
            sql_text = resp_json.get("sql", "")

            # Print rich Ollama & synthesis trace
            print("-" * 70, flush=True)
            print(f"[Ollama & AI Pipeline Trace]", flush=True)
            print(f" • Question : {question}", flush=True)
            print(f" • Guardrail: {guard_info.get('status')} ({guard_info.get('model')}, {guard_info.get('latency_ms')}ms)", flush=True)
            if sql_text:
                print(f" • SQL Query: {sql_text}", flush=True)
            print(f" • Output   : {answer_text}", flush=True)
            print(f" • Latency  : {total_latency}ms", flush=True)
            print("=" * 70 + "\n", flush=True)

            return Response(
                json.dumps(resp_json),
                status=200 if resp.status_code == 200 else resp.status_code,
                headers={'Content-Type': 'application/json', **cors_headers}
            )
        except Exception as e:
            total_latency = round((time.time() - start_time) * 1000, 1)
            print(f"[AI Chatbot Error] {str(e)}", flush=True)
            print("=" * 70 + "\n", flush=True)
            error_response = json.dumps({
                "answer": f"Could not reach the AI service. Make sure n8n is running on port 5678. (Details: {str(e)})",
                "guardrail": guard_info
            })
            return Response(error_response, status=200, headers={'Content-Type': 'application/json', **cors_headers})

    csrf.exempt(ai_chat_proxy)


