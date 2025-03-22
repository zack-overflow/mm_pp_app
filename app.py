from flask import Flask, jsonify, request
import json
import os
import pandas as pd
from constants import JSON_FILE_PATH
from flask_cors import CORS
from get_entrant_data import get_entrant_data
from create_scoreboard import create_scoreboard
from perfect_bracket import perfect_bracket
from get_player_data import get_player_data

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

@app.route("/pk/perfect_bracket", methods=["GET"])
def perfect_bracket_endpoint():
    """
    Returns the top 15 players in the competition and how many entrants picked them
    """
    try:
        # Get data from the perfect_bracket function (renamed to get_perfect_bracket_data)
        perfect_bracket_data = perfect_bracket()
        return jsonify(perfect_bracket_data)
    except Exception as e:
        # More detailed error handling
        print(f"Error in perfect_bracket_endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/perfect_bracket", methods=["GET"])
def perfect_bracket_nk_endpoint():
    """
    Returns the top 15 players in the competition and how many entrants picked them
    """
    try:
        # Get data from the perfect_bracket function (renamed to get_perfect_bracket_data)
        perfect_bracket_data = perfect_bracket(pikap=False)
        return jsonify(perfect_bracket_data)
    except Exception as e:
        # More detailed error handling
        print(f"Error in perfect_bracket_endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@app.route("/player/<player_name>")
@app.route("/pk/player/<player_name>")
def get_player(player_name):
    """
    Returns the player data for a specific player.
    """
    try:
        # Parse the player name from the URL
        player_name = player_name.replace("-", " ").upper()
        player_data = get_player_data(player_name)
        
        if player_data:
            return jsonify(player_data)
        else:
            return jsonify({"error": "Player not found"}), 404
    except Exception as e:
        print(f"Error in get_player: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)