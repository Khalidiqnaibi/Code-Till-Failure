from flask import Flask
from flask_cors import CORS

from routes.tickets   import tickets_bp
from routes.documents import documents_bp
from routes.roads     import roads_bp
from routes.shops     import shops_bp

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Register all module blueprints
    app.register_blueprint(tickets_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(roads_bp)
    app.register_blueprint(shops_bp)

    @app.get("/health")
    def health():
        return {"status": "ok", "app": "Hebron Guide API"}

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
    