import flask
from flask import request, json, jsonify
import requests
import flask_mysqldb
import os
from flask_mysqldb import MySQL

app = flask.Flask(__name__)
app.config["DEBUG"] = True

app.config['MYSQL_HOST'] = os.getenv("MYSQL_SERVICE_HOST")
app.config['MYSQL_USER'] = 'flaskuser'
app.config['MYSQL_PASSWORD'] = os.getenv("db_flask_password")
app.config['MYSQL_DB'] = os.getenv("db_name")
app.config['AUTH_PLUGIN'] = 'mysql_native_password'
MySQL = MySQL(app)

@app.route("/api", methods=["GET"])
def index():
    data = requests.get('https://randomapi.com/api/6de6abfedb24f889e0b5f675edc50deb')
    #data = requests.get('https://mdn.github.io/learning-area/javascript/oojs/json/superheroes.json')
    return data.json()

@app.route("/inserthost",methods=['POST'])
def inserthost():
    data = requests.get('https://randomapi.com/api/6de6abfedb24f889e0b5f675edc50deb').json()
    username = data['results'][0][0]['first']
    cur = MySQL.connection.cursor()
    cur.execute("""INSERT INTO users(name) VALUES(%s)""",(username,))
    MySQL.connection.commit()
    cur.close()

    return username


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port="5000")