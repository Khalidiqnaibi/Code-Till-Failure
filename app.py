'''
The entry point to to the app 

architechure : use flask for backend and react native for the frontend app
'''

import os

from flask import Flask , render_template
from routes.auth import auth_blueprint
from flask_cors import CORS
# from routes.doc_route import doc_blueprint
# from routes.shop_route import shop_blueprint
# from routes.ticket_route import ticket_blueprint

from dotenv import load_dotenv

from routes.tickets   import tickets_bp
from routes.documents import documents_bp
from routes.roads     import roads_bp
from routes.shops     import shops_bp

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.secret_key = os.environ.get("SECRET")

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
    
