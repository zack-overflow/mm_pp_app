from flask import Flask, jsonify, request
import json
import os
from get_entrant_data import get_entrant_data
from create_scoreboard import create_scoreboard
from constants import JSON_FILE_PATH
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/')
def hello_world():
    return 'Welcome to the madness, Gottesman style!'

@app.route('/scoreboard')
def scoreboard():
    try:
        data = create_scoreboard(pikap=False)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify("error: scoreboard not found"), 404

@app.route('/pk/scoreboard')
def scoreboard_pk():
    try:
        data = create_scoreboard(pikap=True)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify("error: scoreboard not found"), 404

@app.route("/update_bk", methods=["POST"])
def update_bk():
    """
    Accepts a JSON payload via POST and overwrites the scoreboard.json file.
    Example of expected JSON payload in the request body:
       [
         {"entrantName": "Alice", "score": 120},
         {"entrantName": "Bob", "score": 100}
       ]
    """
    try:
        # 1. Get the JSON from the request
        data = request.get_json(force=True)  # force=True to parse even without 'Content-Type: application/json'

        # 2. Write/overwrite the file
        with open(JSON_FILE_PATH, "w") as f:
            json.dump(data, f, indent=2)
        
        # 3. Log that it was updated
        print(f"Updated {JSON_FILE_PATH} with new data: {data}")

        return jsonify({"status": "success"}), 200

    except Exception as e:
        # Handle any error (JSON parse error, file write error, etc.)
        return jsonify({"status": "error", "message": str(e)}), 400
    
# Get page from a specific entrant
@app.route("/entrant/<entrant_name>")
def get_entrant(entrant_name):
    try:
        data = get_entrant_data(entrant_name)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify("error: player data not found"), 404
    
@app.route("/pk/entrant/<entrant_name>")
def get_entrant_pk(entrant_name):
    try:
        data = get_entrant_data(entrant_name, pikap=True)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify("error: player data not found"), 404
    

