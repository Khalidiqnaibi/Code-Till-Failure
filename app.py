'''
The entry point to to the app 

architechure : use flask for backend and react native for the frontend app
'''

import os

from flask import Flask , render_template
from routes.auth import auth_blueprint
# from routes.doc_route import doc_blueprint
# from routes.shop_route import shop_blueprint
# from routes.ticket_route import ticket_blueprint

from dotenv import load_dotenv


load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET")

app.register_blueprint(auth_blueprint, url_prefix="/auth")
 

@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True ,port=5000 , host= "0.0.0.0")