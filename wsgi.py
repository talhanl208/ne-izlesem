"""WSGI giriş noktası (PythonAnywhere / gunicorn / flask run)."""
import os

from neizlesem import create_app

app = create_app()

if __name__ == "__main__":
    # Hata ayıklama modu sadece FLASK_DEBUG=1 verilirse açılır; sunucuda asla açma.
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
