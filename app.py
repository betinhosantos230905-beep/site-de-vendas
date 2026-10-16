"""SALTY - ponto de entrada. O Flask serve o frontend e a API no mesmo projeto."""

from pathlib import Path

from flask import Flask, jsonify, send_from_directory

from backend.config import Config
from backend.routes.admin import admin_bp
from backend.routes.catalog import catalog_bp
from backend.routes.orders import orders_bp


FRONTEND_DIR = Path(__file__).parent / "public"


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder=None,
        static_url_path="",
    )

    app.config.from_object(Config)

    # ConfiguraÃƒÂ§ÃƒÂµes dos cookies da sessÃƒÂ£o.
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = not app.debug

    # Rotas da API.
    app.register_blueprint(catalog_bp, url_prefix="/api")
    app.register_blueprint(orders_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

    @app.get("/")
    def index():
        # A pÃƒÂ¡gina principal abre direto no cardÃƒÂ¡pio.
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.get("/<path:filename>")
    def public_files(filename):
        return send_from_directory(FRONTEND_DIR, filename)
    @app.errorhandler(404)
    def not_found(_):
        return jsonify({
            "error": "Recurso nÃƒÂ£o encontrado."
        }), 404

    return app


app = create_app()

if __name__ == "__main__":
    app = create_app()
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG,
    )
