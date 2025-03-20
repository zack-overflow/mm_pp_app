from flask import Flask, jsonify, request
import json
import os

# Path to the file you want to overwrite
JSON_FILE_PATH = "/var/data/scoreboard.json"

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Welcome to the madness, Gottesman style!'

@app.route('/scoreboard')
def scoreboard():
    try:
        with open(JSON_FILE_PATH, 'r') as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify("error: scoreboard not found"), 404

@app.route("/update_scoreboard", methods=["POST"])
def update_scoreboard():
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

        return jsonify({"status": "success"}), 200

    except Exception as e:
        # Handle any error (JSON parse error, file write error, etc.)
        return jsonify({"status": "error", "message": str(e)}), 400
