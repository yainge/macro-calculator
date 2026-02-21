"""
app.py — Flask application entry point.

Run with: python app.py
Then open: http://localhost:5000
"""

import os
from flask import Flask, render_template, request, jsonify

import foods as foods_module
from foods import search_foods
from database import init_db, get_goals, upsert_goals, get_log, insert_log_entry, delete_log_entry

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config["SECRET_KEY"] = "macro-calculator-local"


# ── Page ──────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── Goals ─────────────────────────────────────────────────────

@app.route("/api/goals", methods=["GET"])
def api_get_goals():
    return jsonify(get_goals())


@app.route("/api/goals", methods=["POST"])
def api_set_goals():
    data = request.get_json(silent=True) or {}
    try:
        protein = float(data["protein_g"])
        fat     = float(data["fat_g"])
        carbs   = float(data["carbs_g"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "protein_g, fat_g, and carbs_g are required numbers"}), 400

    if protein < 0 or fat < 0 or carbs < 0:
        return jsonify({"error": "Goals cannot be negative"}), 400

    upsert_goals(protein, fat, carbs)
    return jsonify({"ok": True})


# ── Foods ─────────────────────────────────────────────────────

@app.route("/api/foods")
def api_foods():
    q = request.args.get("q", "")
    results = search_foods(q, limit=50)
    return jsonify(results)


# ── Log ───────────────────────────────────────────────────────

@app.route("/api/log", methods=["GET"])
def api_get_log():
    entries, totals = get_log()
    return jsonify({"entries": entries, "totals": totals})


@app.route("/api/log", methods=["POST"])
def api_add_log():
    data = request.get_json(silent=True) or {}

    description = str(data.get("description", "")).strip()
    if not description:
        return jsonify({"error": "description is required"}), 400

    try:
        protein = float(data["protein_g"])
        fat     = float(data["fat_g"])
        carbs   = float(data["carbs_g"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "protein_g, fat_g, and carbs_g are required numbers"}), 400

    if protein < 0 or fat < 0 or carbs < 0:
        return jsonify({"error": "Macro values cannot be negative"}), 400

    calories_raw = data.get("calories")
    calories = float(calories_raw) if calories_raw not in (None, "", "null") else None

    entry_id = insert_log_entry(description, protein, fat, carbs, calories)
    return jsonify({"ok": True, "id": entry_id})


@app.route("/api/log/<int:entry_id>", methods=["DELETE"])
def api_delete_log(entry_id):
    deleted = delete_log_entry(entry_id)
    if deleted:
        return jsonify({"ok": True})
    return jsonify({"error": "Entry not found or does not belong to today"}), 404


# ── Startup ───────────────────────────────────────────────────

if __name__ == "__main__":
    init_db(app)
    foods_module.FOODS = foods_module.load_foods(os.path.join(BASE_DIR, "data", "foods.csv"))
    app.run(debug=True, host="0.0.0.0", port=5000)
