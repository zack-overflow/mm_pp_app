from flask import Flask, jsonify, request
import json
import os
import pandas as pd
from constants import (
    PLAYER_SCORING_DATA_JSON_FILE_PATH,
    PROJECTION_PLAYER_SCORING_DATA_JSON_FILE_PATH,
    TEAMS_ALIVE_MASK_JSON_FILE_PATH,
    TEAM_IN_PROGRESS_MASK_JSON_FILE_PATH,
    PROJECTIONS_JSON_FILE_PATH,
    PK_PROJECTIONS_JSON_FILE_PATH,
    ENTRIES_FILE_PATH,
    ENTRIES_WRITE_FILE_PATH,
    PK_ENTRIES_FILE_PATH,
)
from flask_cors import CORS
from get_entrant_data import get_entrant_data
from create_scoreboard import create_scoreboard
from perfect_bracket import perfect_bracket
from get_player_data import get_player_data
from pick_analysis import get_pick_analysis
from teams_alive import get_teams_alive_mask
from teams_in_progress import get_team_in_progress_mask
from werkzeug.security import generate_password_hash, check_password_hash


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
        return jsonify("error: Zack is updating the app..."), 404

@app.route('/pk/scoreboard')
def scoreboard_pk():
    try:
        data = create_scoreboard(pikap=True)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify("error: Zack is updating the app..."), 404

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
        payload = request.get_json(force=True)  # force=True to parse even without 'Content-Type: application/json'

        # Backwards compatibility: old clients POST only player scoring data.
        if isinstance(payload, dict) and "player_scoring_data" in payload:
            player_data = payload.get("player_scoring_data", {})
            projection_player_data = payload.get("projection_player_scoring_data")
            teams_alive_mask = payload.get("teams_alive_mask")
            team_in_progress_mask = payload.get("team_in_progress_mask")
        else:
            player_data = payload
            projection_player_data = None
            teams_alive_mask = None
            team_in_progress_mask = None

        # 2. Write/overwrite the file
        with open(PLAYER_SCORING_DATA_JSON_FILE_PATH, "w") as f:
            json.dump(player_data, f, indent=2)

        if projection_player_data is not None:
            with open(PROJECTION_PLAYER_SCORING_DATA_JSON_FILE_PATH, "w") as f:
                json.dump(projection_player_data, f, indent=2)

        if teams_alive_mask is not None:
            with open(TEAMS_ALIVE_MASK_JSON_FILE_PATH, "w") as f:
                json.dump(teams_alive_mask, f, indent=2)

        if team_in_progress_mask is not None:
            with open(TEAM_IN_PROGRESS_MASK_JSON_FILE_PATH, "w") as f:
                json.dump(team_in_progress_mask, f, indent=2)
        
        # 3. Log that it was updated
        print(f"Updated {PLAYER_SCORING_DATA_JSON_FILE_PATH} with new data")
        if projection_player_data is not None:
            print(f"Updated {PROJECTION_PLAYER_SCORING_DATA_JSON_FILE_PATH} with final-only projection data")
        if teams_alive_mask is not None:
            print(f"Updated {TEAMS_ALIVE_MASK_JSON_FILE_PATH} with live team statuses")
        if team_in_progress_mask is not None:
            print(f"Updated {TEAM_IN_PROGRESS_MASK_JSON_FILE_PATH} with in-progress team statuses")

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
        return jsonify("error: entrant data not found"), 404
    
@app.route("/pk/entrant/<entrant_name>")
def get_entrant_pk(entrant_name):
    try:
        data = get_entrant_data(entrant_name, pikap=True)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify("error: entrant data not found"), 404

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


@app.route("/pick_analysis", methods=["GET"])
def pick_analysis_endpoint():
    try:
        return jsonify(get_pick_analysis(pikap=False))
    except FileNotFoundError:
        return jsonify("error: Zack is updating the app..."), 404
    except Exception as e:
        print(f"Error in pick_analysis_endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/pk/pick_analysis", methods=["GET"])
def pick_analysis_pk_endpoint():
    try:
        return jsonify(get_pick_analysis(pikap=True))
    except FileNotFoundError:
        return jsonify("error: Zack is updating the app..."), 404
    except Exception as e:
        print(f"Error in pick_analysis_pk_endpoint: {str(e)}")
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
        player_data = get_player_data(player_name, pikap=request.path.startswith("/pk/"))
        
        if player_data:
            return jsonify(player_data)
        else:
            return jsonify({"error": "Player not found"}), 404
    except Exception as e:
        print(f"Error in get_player: {str(e)}")
        return jsonify({"error": str(e)}), 500

def _load_entries(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)

def _save_entries(entries, path):
    with open(path, "w") as f:
        json.dump(entries, f, indent=2)

def _entries_path_for_request():
    return PK_ENTRIES_FILE_PATH if request.path.startswith("/pk/") else ENTRIES_FILE_PATH


def _entries_write_path_for_request():
    return PK_ENTRIES_FILE_PATH if request.path.startswith("/pk/") else ENTRIES_WRITE_FILE_PATH


def _projections_path_for_request():
    return PK_PROJECTIONS_JSON_FILE_PATH if request.path.startswith("/pk/") else PROJECTIONS_JSON_FILE_PATH

def _read_player_catalog():
    df = pd.read_csv("espn_players_2026.csv")
    catalog = {}
    team_seed_map = {}
    for _, row in df.iterrows():
        player_name = str(row["player_name"]).strip()
        team_name = str(row["team_name"]).strip()
        seed = int(row["seed"])
        catalog[player_name.upper()] = {
            "name": player_name.title(),
            "team": team_name,
            "seed": seed,
        }
        team_seed_map[team_name] = seed
    return catalog, team_seed_map


def _read_player_scoring_data():
    if not os.path.exists(PLAYER_SCORING_DATA_JSON_FILE_PATH):
        return {}
    with open(PLAYER_SCORING_DATA_JSON_FILE_PATH, "r") as f:
        return json.load(f)


def _read_projection_player_scoring_data():
    if not os.path.exists(PROJECTION_PLAYER_SCORING_DATA_JSON_FILE_PATH):
        return {}
    with open(PROJECTION_PLAYER_SCORING_DATA_JSON_FILE_PATH, "r") as f:
        return json.load(f)


def _read_projection_snapshot(path=None):
    path = path or PROJECTIONS_JSON_FILE_PATH
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


@app.route("/players", methods=["GET"])
@app.route("/pk/players", methods=["GET"])
def get_players():
    try:
        df = pd.read_csv("espn_players_2026.csv")
        df = df.iloc[df["player_name"].str.split().str[-1].argsort().values]
        players = [
            {"name": row["player_name"].title(), "team": row["team_name"], "seed": int(row["seed"])}
            for _, row in df.iterrows()
        ]
        return jsonify(players)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/projection_inputs", methods=["GET"])
@app.route("/pk/projection_inputs", methods=["GET"])
def projection_inputs():
    try:
        player_catalog, team_seed_map = _read_player_catalog()
        entries = _load_entries(_entries_path_for_request())
        public_entries = {
            entrant_name: {"picks": entry.get("picks", [])}
            for entrant_name, entry in entries.items()
        }
        return jsonify(
            {
                "entries": public_entries,
                "player_scoring_data": _read_player_scoring_data(),
                "projection_player_scoring_data": _read_projection_player_scoring_data(),
                "teams_alive_mask": get_teams_alive_mask(),
                "team_in_progress_mask": get_team_in_progress_mask(),
                "player_catalog": player_catalog,
                "team_seed_map": team_seed_map,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/update_projections", methods=["POST"])
@app.route("/pk/update_projections", methods=["POST"])
def update_projections():
    try:
        payload = request.get_json(force=True)
        with open(_projections_path_for_request(), "w") as f:
            json.dump(payload, f, indent=2)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/projections", methods=["GET"])
@app.route("/pk/projections", methods=["GET"])
def projections():
    try:
        snapshot = _read_projection_snapshot(_projections_path_for_request())
        if snapshot is None:
            return jsonify({"error": "Projection snapshot not available"}), 404
        return jsonify(snapshot)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/entry/create", methods=["POST"])
@app.route("/pk/entry/create", methods=["POST"])
def entry_create():
    try:
        data = request.get_json(force=True)
        name = data.get("name", "").strip()
        password = data.get("password", "")
        read_path = _entries_path_for_request()
        write_path = _entries_write_path_for_request()
        entries = _load_entries(read_path)
        if name in entries:
            return jsonify({"success": False, "message": "An entry with that name already exists."})
        entries[name] = {"password": generate_password_hash(password), "picks": []}
        _save_entries(entries, write_path)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/entry/login", methods=["POST"])
@app.route("/pk/entry/login", methods=["POST"])
def entry_login():
    try:
        data = request.get_json(force=True)
        name = data.get("name", "").strip()
        password = data.get("password", "")
        path = _entries_path_for_request()
        entries = _load_entries(path)
        entry = entries.get(name)
        if not entry or not check_password_hash(entry["password"], password):
            return jsonify({"success": False, "message": "Invalid name or password."})
        # Resolve pick names to full player objects
        df = pd.read_csv("espn_players_2026.csv")
        player_map = {row["player_name"].title(): {"name": row["player_name"].title(), "team": row["team_name"], "seed": int(row["seed"])} for _, row in df.iterrows()}
        picks = [player_map[p] for p in entry.get("picks", []) if p in player_map]
        return jsonify({"success": True, "picks": picks})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/entry/picks", methods=["PUT"])
@app.route("/pk/entry/picks", methods=["PUT"])
def entry_picks():
    try:
        data = request.get_json(force=True)
        name = data.get("name", "").strip()
        password = data.get("password", "")
        picks = data.get("picks", [])
        read_path = _entries_path_for_request()
        write_path = _entries_write_path_for_request()
        entries = _load_entries(read_path)
        entry = entries.get(name)
        if not entry or not check_password_hash(entry["password"], password):
            return jsonify({"success": False, "message": "Invalid name or password."})
        entry["picks"] = picks
        _save_entries(entries, write_path)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def _build_projection_inputs(pikap=False):
    player_catalog, team_seed_map = _read_player_catalog()
    entries_path = PK_ENTRIES_FILE_PATH if pikap else ENTRIES_FILE_PATH
    entries = _load_entries(entries_path)
    public_entries = {
        name: {"picks": entry.get("picks", [])}
        for name, entry in entries.items()
    }
    return {
        "entries": public_entries,
        "player_scoring_data": _read_player_scoring_data(),
        "projection_player_scoring_data": _read_projection_player_scoring_data(),
        "teams_alive_mask": get_teams_alive_mask(),
        "player_catalog": player_catalog,
        "team_seed_map": team_seed_map,
    }


@app.route("/bracket", methods=["GET"])
@app.route("/pk/bracket", methods=["GET"])
def bracket():
    try:
        pikap = request.path.startswith("/pk/")
        inputs = _build_projection_inputs(pikap=pikap)
        from projections.pipeline import build_bracket_snapshot
        result = build_bracket_snapshot(inputs)
        return jsonify(result)
    except Exception as e:
        print(f"Error in bracket endpoint: {e}")
        return jsonify({"error": str(e)}), 500


WHATIF_DEFAULT_N_SIMS = 500


@app.route("/whatif", methods=["POST"])
@app.route("/pk/whatif", methods=["POST"])
def whatif():
    try:
        pikap = request.path.startswith("/pk/")
        payload = request.get_json(force=True)
        forced_winners = payload.get("forced_winners", {})
        if not forced_winners:
            return jsonify({"error": "forced_winners is required"}), 400

        model = payload.get("model", "silver")
        if model not in ("kenpom", "silver"):
            return jsonify({"error": "model must be 'kenpom' or 'silver'"}), 400

        print(f"What-if request: forced_winners={forced_winners}, model={model}")
        n_sims = min(int(payload.get("n_sims", WHATIF_DEFAULT_N_SIMS)), 2000)
        from projections.pipeline import build_projection_snapshot
        inputs = _build_projection_inputs(pikap=pikap)

        # Run both baseline and what-if with same sim count for apples-to-apples comparison
        baseline_snapshot = build_projection_snapshot(inputs, n_sims=n_sims, model=model)
        try:
            whatif_snapshot = build_projection_snapshot(
                inputs,
                n_sims=n_sims,
                forced_winners=forced_winners,
                model=model,
            )
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        whatif_snapshot["baseline"] = baseline_snapshot.get("entrant_projections", [])
        return jsonify(whatif_snapshot)
    except Exception as e:
        print(f"Error in whatif endpoint: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
