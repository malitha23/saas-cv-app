import sys
import os
import glob
import traceback

# 1. Add application directory to sys.path
app_path = os.path.dirname(os.path.abspath(__file__))
if app_path not in sys.path:
    sys.path.insert(0, app_path)

# 2. Automatically locate and add cPanel virtualenv site-packages to sys.path
home_dir = os.path.expanduser("~")
exact_venv = os.path.join(home_dir, "virtualenv", "s.tourglobalhub.com", "3.11", "lib", "python3.11", "site-packages")
if os.path.exists(exact_venv) and exact_venv not in sys.path:
    sys.path.insert(0, exact_venv)

possible_venvs = glob.glob(os.path.join(home_dir, "virtualenv", "*", "3.11", "lib", "python*", "site-packages"))
for vp in possible_venvs:
    if vp not in sys.path:
        sys.path.insert(0, vp)

# Global instances for lazy initialization
_wsgi_app = None
_init_error = None


def get_wsgi_app():
    """Lazily load FastAPI and a2wsgi to guarantee instant startup and zero timeout freezes."""
    global _wsgi_app, _init_error
    if _wsgi_app is not None:
        return _wsgi_app, None
    if _init_error is not None:
        return None, _init_error

    try:
        from a2wsgi import ASGIMiddleware
        from app.main import app
        _wsgi_app = ASGIMiddleware(app)
        return _wsgi_app, None
    except Exception:
        _init_error = traceback.format_exc()
        return None, _init_error


def application(environ, start_response):
    path = environ.get("PATH_INFO", "")

    # 1. Fast Diagnostic Endpoint (always responds in < 1ms, proves Passenger is alive)
    if path == "/test-ping":
        output = b"OK - Python 3.11 Passenger WSGI is ALIVE and RESPONSIVE!\n"
        start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8"), ("Content-Length", str(len(output)))])
        return [output]

    # 2. Get WSGI Application (lazy load)
    app_handler, err = get_wsgi_app()

    if err:
        status = "500 Internal Server Error"
        output = (
            f"<html><head><title>Initialization Error</title></head>"
            f"<body style='font-family: monospace; padding: 25px; background: #fff1f0; color: #cf1322;'>"
            f"<h2>⚠️ Application Initialization Error</h2>"
            f"<p><b>Python Version:</b> {sys.version}</p>"
            f"<p><b>Search Path:</b><br>{'<br>'.join(sys.path[:6])}</p>"
            f"<hr><pre style='background: white; padding: 15px; border-radius: 6px; border: 1px solid #ffa39e; overflow: auto;'>"
            f"{err}</pre>"
            f"<p><i>Check if all requirements from requirements.txt are installed via cPanel.</i></p>"
            f"</body></html>"
        ).encode("utf-8")
        start_response(status, [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(output)))])
        return [output]

    # 3. Handle Request
    try:
        return app_handler(environ, start_response)
    except Exception:
        exec_err = traceback.format_exc()
        status = "500 Internal Server Error"
        output = (
            f"<html><head><title>Runtime Error</title></head>"
            f"<body style='font-family: monospace; padding: 25px; background: #fffbe6; color: #d46b08;'>"
            f"<h2>⚠️ Request Runtime Error</h2>"
            f"<hr><pre style='background: white; padding: 15px; border-radius: 6px; border: 1px solid #ffe58f; overflow: auto;'>"
            f"{exec_err}</pre>"
            f"</body></html>"
        ).encode("utf-8")
        start_response(status, [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(output)))])
        return [output]
