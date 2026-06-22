import sys
import os

# Assuming you uploaded the backend folder to /home/yourusername/backend
path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.append(path)

# Import the FastAPI app
from main import app as asgi_app

# PythonAnywhere uses WSGI, so we must adapt our ASGI FastAPI app to WSGI
from a2wsgi import ASGIMiddleware

# This is the WSGI application callable that PythonAnywhere looks for
application = ASGIMiddleware(asgi_app)
