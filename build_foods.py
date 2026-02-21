"""
build_foods.py — One-time preprocessing script.

Reads food sources and outputs data/foods.csv for the macro calculator app.

Sources (in priority order):
  1. MyFoodData Nutrition Facts Spreadsheet (SR Legacy + FNDDS) — 14K foods, per 100g
  2. USDA FoodData Central Foundation Foods CSVs — ~300 additional foundation foods

Usage:
    python build_foods.py

Output: data/foods.csv
"""

import csv
import os
import sys

MYFOODDATA_XLSX = "Data/MyFoodData Nutrition Facts SpreadSheet Release 1.4.xlsx"
USDA_DIR = "Data/FoodData_Central_foundation_food_csv_2025-04-24"
OUTPUT = "data/foods.csv"

# USDA nutrient IDs
NUTRIENT_IDS = {
    "protein_g": 1003,
    "fat_g":     1004,
    "carbs_g":   1005,
    "calories":  1008,
}


def safe_float(val):
    if val is None:
        return None
    try:
        v = float(str(val).strip().strip('"'))
        return None if v != v else v  # NaN check
    except (ValueError, TypeError):
        return None


def strip_quotes(val):
    return str(val).strip().strip('"').strip()


# ──────────────────────────────────────────────────────────────
# Source 1: MyFoodData xlsx (primary — 14K foods, all per 100g)
# ──────────────────────────────────────────────────────────────

def load_myfooddata():
    """Returns list of dicts with keys: name, protein_g, fat_g, carbs_g, calories, category."""
    if not os.path.isfile(MYFOODDATA_XLSX):
        print(f"  WARNING: {MYFOODDATA_XLSX} not found, skipping.", file=sys.stderr)
        return []

    try:
        import openpyxl
    except ImportError:
        print("  WARNING: openpyxl not installed. Run: pip install openpyxl", file=sys.stderr)
        return []

    print(f"  Reading {MYFOODDATA_XLSX}...")
    wb = openpyxl.load_workbook(MYFOODDATA_XLSX, read_only=True, data_only=True)
    ws = wb["SR Legacy and FNDDS"]

    # Header is at row 4 (0-indexed: row 3)
    # Columns: ID, Name, Food Group, Calories, Fat(g), Protein(g), Carbohydrate(g), ...
    COL_NAME = 1
    COL_GROUP = 2
    COL_CALORIES = 3
    COL_FAT = 4
    COL_PROTEIN = 5
    COL_CARBS = 6

    foods = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i < 4:  # Skip title rows and header
            continue
        if row[0] is None:
            continue

        name = str(row[COL_NAME]).strip() if row[COL_NAME] else None
        if not name or name == "None":
            continue

        protein = safe_float(row[COL_PROTEIN])
        fat = safe_float(row[COL_FAT])
        carbs = safe_float(row[COL_CARBS])
        calories = safe_float(row[COL_CALORIES])
        category = str(row[COL_GROUP]).strip() if row[COL_GROUP] else ""

        if protein is None or fat is None or carbs is None:
            continue

        foods.append({
            "name": name,
            "serving_size": 100.0,
            "serving_unit": "g",
            "protein_g": protein,
            "fat_g": fat,
            "carbs_g": carbs,
            "calories": calories,
            "category": category,
        })

    wb.close()
    print(f"  Loaded {len(foods)} foods from MyFoodData")
    return foods


# ──────────────────────────────────────────────────────────────
# Source 2: USDA Foundation Foods CSVs (supplement)
# ──────────────────────────────────────────────────────────────

def load_usda_csv(filename):
    path = os.path.join(USDA_DIR, filename)
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_foundation_foods():
    """Returns list of dicts in same format as load_myfooddata()."""
    if not os.path.isdir(USDA_DIR):
        print(f"  WARNING: {USDA_DIR} not found, skipping USDA data.", file=sys.stderr)
        return []

    print(f"  Reading USDA Foundation Foods CSVs...")

    # Nutrient id -> key
    nutrients_raw = load_usda_csv("nutrient.csv")
    target_ids = {str(v): k for k, v in NUTRIENT_IDS.items()}
    nutrient_nbr_map = {"203": "protein_g", "204": "fat_g", "205": "carbs_g", "208": "calories"}
    id_to_key = {}
    for row in nutrients_raw:
        nid = strip_quotes(row.get("id", ""))
        nbr = strip_quotes(row.get("nutrient_nbr", ""))
        if nid in target_ids:
            id_to_key[nid] = target_ids[nid]
        elif nbr in nutrient_nbr_map and nid not in id_to_key:
            id_to_key[nid] = nutrient_nbr_map[nbr]

    # Categories
    cat_raw = load_usda_csv("food_category.csv")
    category_map = {strip_quotes(r["id"]): strip_quotes(r["description"]) for r in cat_raw if r.get("id")}

    # Foods — only foundation_food type for supplement quality
    food_raw = load_usda_csv("food.csv")
    foods_dict = {}
    for row in food_raw:
        if strip_quotes(row.get("data_type", "")) != "foundation_food":
            continue
        fdc_id = strip_quotes(row.get("fdc_id", ""))
        desc = strip_quotes(row.get("description", ""))
        cat_id = strip_quotes(row.get("food_category_id", ""))
        if fdc_id and desc:
            foods_dict[fdc_id] = {"description": desc, "category_id": cat_id}

    # Nutrient data
    nutrient_data = {}
    nutrient_path = os.path.join(USDA_DIR, "food_nutrient.csv")
    with open(nutrient_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fdc_id = strip_quotes(row.get("fdc_id", ""))
            if fdc_id not in foods_dict:
                continue
            nid = strip_quotes(row.get("nutrient_id", ""))
            if nid not in id_to_key:
                continue
            amount = safe_float(row.get("amount", ""))
            if amount is None:
                continue
            if fdc_id not in nutrient_data:
                nutrient_data[fdc_id] = {}
            nutrient_data[fdc_id][id_to_key[nid]] = amount

    # Portions
    portions_raw = load_usda_csv("food_portion.csv")
    units_raw = load_usda_csv("measure_unit.csv")
    unit_map = {strip_quotes(r["id"]): strip_quotes(r["name"]) for r in units_raw if r.get("id")}
    portions = {}
    for row in portions_raw:
        fdc_id = strip_quotes(row.get("fdc_id", ""))
        if fdc_id not in foods_dict or fdc_id in portions:
            continue
        gram_weight = safe_float(row.get("gram_weight", ""))
        amount = safe_float(row.get("amount", ""))
        unit_id = strip_quotes(row.get("measure_unit_id", ""))
        unit_name = unit_map.get(unit_id, "g")
        if gram_weight and gram_weight > 0:
            portions[fdc_id] = {
                "gram_weight": gram_weight,
                "serving_size": amount if amount and amount > 0 else gram_weight,
                "serving_unit": unit_name or "g",
            }

    # Build output
    foods = []
    for fdc_id, food_info in foods_dict.items():
        macros = nutrient_data.get(fdc_id, {})
        if "protein_g" not in macros or "fat_g" not in macros or "carbs_g" not in macros:
            continue

        if fdc_id in portions:
            p = portions[fdc_id]
            gram_weight = p["gram_weight"]
            serving_size = p["serving_size"]
            serving_unit = p["serving_unit"]
        else:
            gram_weight = 100.0
            serving_size = 100.0
            serving_unit = "g"

        scale = gram_weight / 100.0
        foods.append({
            "name": food_info["description"],
            "serving_size": serving_size,
            "serving_unit": serving_unit,
            "protein_g": round(macros["protein_g"] * scale, 1),
            "fat_g": round(macros["fat_g"] * scale, 1),
            "carbs_g": round(macros["carbs_g"] * scale, 1),
            "calories": round(macros["calories"] * scale, 1) if macros.get("calories") is not None else None,
            "category": category_map.get(food_info["category_id"], ""),
        })

    print(f"  Loaded {len(foods)} foundation foods from USDA CSVs")
    return foods


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main():
    print("Loading food sources...")

    primary = load_myfooddata()       # ~14K foods, per 100g
    supplement = load_foundation_foods()  # ~300 foods with real serving sizes

    # Merge: MyFoodData first, then add any supplement foods not already present
    seen = {f["name"].lower().strip() for f in primary}
    added_from_supplement = 0
    for food in supplement:
        key = food["name"].lower().strip()
        if key not in seen:
            primary.append(food)
            seen.add(key)
            added_from_supplement += 1

    print(f"\nMerge summary:")
    print(f"  MyFoodData:            {len(primary) - added_from_supplement} foods")
    print(f"  Added from USDA:       {added_from_supplement} new foods")
    print(f"  Total unique foods:    {len(primary)}")

    # Sort alphabetically by name
    primary.sort(key=lambda f: f["name"].lower())

    # Write output
    os.makedirs("data", exist_ok=True)
    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "serving_size", "serving_unit", "protein_g", "fat_g", "carbs_g", "calories", "category"])
        for food in primary:
            writer.writerow([
                food["name"],
                food["serving_size"],
                food["serving_unit"],
                round(food["protein_g"], 1),
                round(food["fat_g"], 1),
                round(food["carbs_g"], 1),
                round(food["calories"], 1) if food.get("calories") is not None else "",
                food["category"],
            ])

    print(f"\nOutput written to: {OUTPUT}")


if __name__ == "__main__":
    main()
