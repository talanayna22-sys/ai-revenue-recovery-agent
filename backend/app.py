from flask import Flask, jsonify

try:
    from flask_cors import CORS
except ImportError:  # pragma: no cover - fallback if flask-cors isn't installed yet
    CORS = None

import database as db
from config import Config
from routes import dashboard, cases, ai_agent, audit, guardrails, demo, razorpay_webhook


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    if CORS is not None:
        CORS(app, origins=Config.CORS_ORIGINS, supports_credentials=True)
    else:
        @app.after_request
        def _add_cors_headers(resp):
            origin = "*" if not Config.CORS_ORIGINS else Config.CORS_ORIGINS[0]
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization,X-Razorpay-Signature"
            resp.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
            return resp

    db.init_db()

    app.register_blueprint(dashboard.bp)
    app.register_blueprint(cases.bp)
    app.register_blueprint(ai_agent.bp)
    app.register_blueprint(audit.bp)
    app.register_blueprint(guardrails.bp)
    app.register_blueprint(demo.bp)
    app.register_blueprint(razorpay_webhook.bp)

    @app.get("/api/health")
    def health():
        ok, info = db.health_check()
        return jsonify({
            "status": "ok" if ok else "error",
            "database_engine": Config.DB_ENGINE,
            "database_detail": info,
            "payment_mode": Config.PAYMENT_MODE,
            "ai_configured": bool(Config.ANTHROPIC_API_KEY),
        }), (200 if ok else 500)

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error", "detail": str(e)}), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
