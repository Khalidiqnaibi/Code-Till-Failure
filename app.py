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
    "https://mlosocwinwylysatnbtm.supabase.co",
    "sb_publishable_BXfqbXN8BV7pqEvMCdPexA_CeV1ERGQ"
)

app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get("SECRET")


# Register all module blueprints
app.register_blueprint(roads_bp)
app.register_blueprint(shops_bp)
app.register_blueprint(auth_bp)

app.config.setdefault("adapter", adapter) 

@app.get("/health")
def health():
    return {"status": "ok", "app": "Hebron Guide API"}




if __name__ == "__main__":
    app.run(debug=True, port=5000)
    
