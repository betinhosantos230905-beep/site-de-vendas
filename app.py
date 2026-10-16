"""SALTY - ponto de entrada. O Flask serve o frontend e a API no mesmo projeto."""

from pathlib import Path

from flask import Flask, jsonify, send_from_directory

from backend.config import Config
from backend.routes.admin import admin_bp
from backend.routes.catalog import catalog_bp
from backend.routes.orders import orders_bp


FRONTEND_DIR = Path(__file__).parent / "frontend"


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=str(FRONTEND_DIR),
        static_url_path="",
    )

    app.config.from_object(Config)

    # Configurações dos cookies da sessão.
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = not app.debug

    # Rotas da API.
    app.register_blueprint(catalog_bp, url_prefix="/api")
    app.register_blueprint(orders_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

    @app.get("/")
    def index():
        # A página principal abre direto no cardápio.
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({
            "error": "Recurso não encontrado."
        }), 404

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG,
    )
