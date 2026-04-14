'''
The entry point to to the app 

architechure : use flask for backend and react native for the frontend app
'''

from flask import Flask , render_template
from dotenv import load_dotenv


load_dotenv()

app = Flask()

app.route("/",methods= ["GET"])
def index():
    return render_template(index.html)


if __name__ == "__main__":
    app.run()