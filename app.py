'''
The entry point to to the app 

architechure : use flask for backend and react native for the frontend app
'''

import os

from flask import Flask , render_template
from routes.auth_route import auth_bp
from flask_cors import CORS
from dotenv import load_dotenv

from db.supabase_adapter import SupabaseAdapter
from routes.roads_route     import roads_bp
from routes.shop_route     import shops_bp

load_dotenv()
adapter = SupabaseAdapter(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

print(adapter.list_document_templates())
def create_app():
    app = Flask(__name__)
    CORS(app)
    app.secret_key = os.environ.get("SECRET")
    
    app.config["ADAPTER"] = adapter

    # Register all module blueprints
    app.register_blueprint(roads_bp)
    app.register_blueprint(shops_bp)
    app.register_blueprint(auth_bp)

    @app.get("/health")
    def health():
        return {"status": "ok", "app": "Hebron Guide API"}

    return app



if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
    
