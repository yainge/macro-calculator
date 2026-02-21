"""
foods.py — In-memory food list loaded from data/foods.csv.

FOODS is populated once at app startup via load_foods().
search_foods() does a fast substring match on name and category.
"""

import csv
import os
import sys

FOODS = []   # module-level list populated by load_foods()


def load_foods(csv_path: str) -> list:
    if not os.path.isfile(csv_path):
        print(f"WARNING: foods CSV not found at {csv_path!r}. "
              "Common foods picker will be empty. "
              "Run build_foods.py to generate it.", file=sys.stderr)
        return []

    foods = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                serving_size = float(row["serving_size"])
                if serving_size <= 0:
                    continue
                foods.append({
                    "name":         row["name"].strip(),
                    "serving_size": serving_size,
                    "serving_unit": row["serving_unit"].strip() or "g",
                    "protein_g":    float(row["protein_g"]),
                    "fat_g":        float(row["fat_g"]),
                    "carbs_g":      float(row["carbs_g"]),
                    "calories":     float(row["calories"]) if row.get("calories") else None,
                    "category":     row.get("category", "").strip(),
                })
            except (ValueError, KeyError):
                continue  # skip malformed rows

    print(f"Loaded {len(foods)} foods from {csv_path}", file=sys.stderr)
    return foods


def search_foods(query: str, limit: int = 50) -> list:
    q = query.strip().lower()
    if not q:
        return FOODS[:limit]
    return [
        f for f in FOODS
        if q in f["name"].lower() or q in f["category"].lower()
    ][:limit]
