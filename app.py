from flask import Flask, render_template, redirect, url_for, request, Response, jsonify, send_file
import json
import os
import io
from datetime import datetime
from collections import Counter
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill

app = Flask(__name__)


# ============================================================
# DEFAULT USUAL SHOP
# ============================================================

DEFAULT_USUAL_SHOP = {
    "Fridge / Veg": [
        "Toms",
        "Cuc",
        "Onions",
        "Pots",
        "Beetroots",
        "Celery",
        "Cheese",
    ],
    "Freezer": [
        "Breads / rolls",
        "Meats",
        "Chips",
        "Ice cream",
    ],
    "Cleaning Products": [
        "Floor cleaner",
        "Bleach",
        "Bin bags",
        "Lenor",
        "Wash powder",
        "Wash up liquid",
    ],
    "Bathroom Products": [
        "Toothpaste",
        "Loo roll",
    ],
    "Dry Goods": [
        "Breads",
        "Cereals",
        "Carton milk",
        "Oat milk",
    ],
    "Tinned Products": [
        "Beans",
        "Soup",
        "Tea bags",
        "Instant coffee",
    ],
}


# ============================================================
# FILE NAMES
# ============================================================

USUAL_SHOP_FILE = "usual_shop.json"
TODAY_FILE = "today_list.json"
CHECKED_FILE = "checked_items.json"
HISTORY_FILE = "shopping_history.json"


# ============================================================
# LOAD / SAVE FUNCTIONS
# ============================================================

def load_usual_shop():
    if os.path.exists(USUAL_SHOP_FILE):
        with open(USUAL_SHOP_FILE, "r") as file:
            return json.load(file)

    return DEFAULT_USUAL_SHOP.copy()


def save_usual_shop():
    with open(USUAL_SHOP_FILE, "w") as file:
        json.dump(usual_shop, file, indent=4)


def load_today_list():
    if os.path.exists(TODAY_FILE):
        with open(TODAY_FILE, "r") as file:
            return json.load(file)

    return []


def save_today_list():
    with open(TODAY_FILE, "w") as file:
        json.dump(today_list, file)


def load_checked_items():
    if os.path.exists(CHECKED_FILE):
        with open(CHECKED_FILE, "r") as file:
            return set(json.load(file))

    return set()


def save_checked_items():
    with open(CHECKED_FILE, "w") as file:
        json.dump(list(checked_items), file)


def load_shopping_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as file:
            return json.load(file)

    return []


def save_shopping_history():
    with open(HISTORY_FILE, "w") as file:
        json.dump(shopping_history, file, indent=4)


def format_duration(started_at, stopped_at):
    if not started_at or not stopped_at:
        return None

    try:
        start = datetime.fromisoformat(started_at)
        stop = datetime.fromisoformat(stopped_at)
    except (TypeError, ValueError):
        return None

    total_seconds = int((stop - start).total_seconds())

    if total_seconds < 0:
        return None

    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours}h {minutes:02d}m"

    if minutes:
        return f"{minutes}m"

    return f"{seconds}s"


# ============================================================
# LOAD CURRENT DATA
# ============================================================

usual_shop = load_usual_shop()
today_list = load_today_list()
checked_items = load_checked_items()
shopping_history = load_shopping_history()


# ============================================================
# HOME
#
# The home page is always rendered from server data. Whether
# a shopping trip is currently "in progress" is a purely local
# (phone-side) idea from here on - the server doesn't need to
# know about it until the trip is completed and synced back.
# ============================================================

@app.route("/")
def home():
    return render_template(
        "home.html",
        shopping_list=today_list,
        checked_items=checked_items,
        usual_shop=usual_shop
    )


# ============================================================
# PREVIOUS LISTS
# ============================================================

@app.route("/previous-lists")
def previous_lists():
    return render_template(
        "previous_lists.html",
        shopping_history=shopping_history
    )


def duration_to_minutes(trip):
    started_at = trip.get("started_at")
    stopped_at = trip.get("stopped_at")

    if not started_at or not stopped_at:
        return None

    try:
        start = datetime.fromisoformat(started_at)
        stop = datetime.fromisoformat(stopped_at)
    except (TypeError, ValueError):
        return None

    minutes = (stop - start).total_seconds() / 60

    if minutes < 0:
        return None

    return minutes


@app.route("/export.xlsx")
def export_history():
    workbook = Workbook()

    header_font = Font(bold=True, color="FFFFFF")
    header_fill_color = "4F7C6B"

    # ------------------------------------------------------------
    # Sheet 1: Shopping History
    # ------------------------------------------------------------
    history_sheet = workbook.active
    history_sheet.title = "Shopping History"

    headers = ["Date", "Items Bought", "Item Count", "Duration"]
    history_sheet.append(headers)

    for column_index, header in enumerate(headers, start=1):
        cell = history_sheet.cell(row=1, column=column_index)
        cell.font = header_font
        cell.fill = PatternFill("solid", fgColor=header_fill_color)

    for trip in shopping_history:
        items = trip.get("items", [])

        history_sheet.append([
            trip.get("date", ""),
            ", ".join(items),
            len(items),
            trip.get("overall_time") or ""
        ])

    history_sheet.column_dimensions["A"].width = 18
    history_sheet.column_dimensions["B"].width = 70
    history_sheet.column_dimensions["C"].width = 12
    history_sheet.column_dimensions["D"].width = 12

    for row in history_sheet.iter_rows(min_row=2):
        row[1].alignment = Alignment(wrap_text=True, vertical="top")

    # ------------------------------------------------------------
    # Sheet 2: Stats
    # ------------------------------------------------------------
    stats_sheet = workbook.create_sheet("Stats")

    total_trips = len(shopping_history)

    item_counter = Counter()
    for trip in shopping_history:
        item_counter.update(trip.get("items", []))

    durations = [
        duration_to_minutes(trip)
        for trip in shopping_history
        if duration_to_minutes(trip) is not None
    ]

    average_minutes = sum(durations) / len(durations) if durations else None

    dates = [trip.get("date") for trip in shopping_history if trip.get("date")]

    def write_stat(row, label, value):
        stats_sheet.cell(row=row, column=1, value=label).font = Font(bold=True)
        stats_sheet.cell(row=row, column=2, value=value)

    write_stat(1, "Total shopping trips", total_trips)
    write_stat(2, "Most recent trip", dates[0] if dates else "-")
    write_stat(3, "Oldest trip in history", dates[-1] if dates else "-")

    if average_minutes is not None:
        write_stat(4, "Average trip duration (minutes)", round(average_minutes, 1))
    else:
        write_stat(4, "Average trip duration (minutes)", "-")

    stats_sheet.cell(row=6, column=1, value="Most frequently bought items").font = Font(bold=True)
    stats_sheet.cell(row=7, column=1, value="Item").font = Font(bold=True)
    stats_sheet.cell(row=7, column=2, value="Times bought").font = Font(bold=True)

    for offset, (item, count) in enumerate(item_counter.most_common(15), start=8):
        stats_sheet.cell(row=offset, column=1, value=item)
        stats_sheet.cell(row=offset, column=2, value=count)

    stats_sheet.column_dimensions["A"].width = 32
    stats_sheet.column_dimensions["B"].width = 16

    # ------------------------------------------------------------
    # Serve the file
    # ------------------------------------------------------------
    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="going_shopping_history.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.route("/previous-lists/remove/<int:index>", methods=["POST"])
def remove_previous_list(index):
    if 0 <= index < len(shopping_history):
        shopping_history.pop(index)
        save_shopping_history()

    return redirect(url_for("previous_lists"))


@app.route("/previous-lists/clear", methods=["POST"])
def clear_previous_lists():
    shopping_history.clear()
    save_shopping_history()
    return redirect(url_for("previous_lists"))


# ============================================================
# MY USUAL SHOP
#
# This page (and Add / Change List below) always needs a
# connection - they edit the shared, permanent list, so there
# is no offline path here, and nothing is duplicated into the
# phone's local storage. What you see is always what is saved.
# ============================================================

@app.route("/usual-shop")
def start_usual_shop():
    return render_template(
        "usual_shop.html",
        usual_shop=usual_shop,
        today_list=today_list
    )


@app.route("/add-selected", methods=["POST"])
def add_selected():
    selected_items = set(request.form.getlist("selected_items"))

    # All products that belong to the Usual Shop
    usual_items = {
        item
        for items in usual_shop.values()
        for item in items
    }

    # Remove Usual Shop items that have been unticked
    today_list[:] = [
        item
        for item in today_list
        if item not in usual_items or item in selected_items
    ]

    # Add newly selected Usual Shop items
    for item in selected_items:
        if item not in today_list:
            today_list.append(item)

    save_today_list()

    return redirect(url_for("home"))


# ============================================================
# ADD / CHANGE LIST
# ============================================================

@app.route("/manage-shop")
def manage_shop():
    return render_template(
        "manage_shop.html",
        usual_shop=usual_shop
    )


@app.route("/manage-shop/add", methods=["POST"])
def manage_shop_add():
    item = request.form.get("item", "").strip()
    category = request.form.get("category", "").strip()
    new_category = request.form.get("new_category", "").strip()

    if not item:
        return redirect(url_for("manage_shop"))

    # Create a new category if one has been entered
    if new_category:
        if new_category not in usual_shop:
            usual_shop[new_category] = []

        category = new_category

    # Add the item to the selected/new category
    if category in usual_shop:
        if item not in usual_shop[category]:
            usual_shop[category].append(item)
            save_usual_shop()

    return redirect(url_for("manage_shop"))


@app.route("/manage-shop/remove", methods=["POST"])
def manage_shop_remove():
    item = request.form.get("item", "").strip()
    category = request.form.get("category", "").strip()

    if category in usual_shop and item in usual_shop[category]:
        usual_shop[category].remove(item)
        save_usual_shop()

    return redirect(url_for("manage_shop"))


@app.route("/manage-shop/change", methods=["POST"])
def manage_shop_change():
    old_item = request.form.get("old_item", "").strip()
    old_category = request.form.get("old_category", "").strip()
    new_item = request.form.get("new_item", "").strip()
    new_category = request.form.get("new_category", "").strip()
    new_category_name = request.form.get("new_category_name", "").strip()

    if (
        old_category not in usual_shop
        or old_item not in usual_shop[old_category]
        or not new_item
    ):
        return redirect(url_for("manage_shop"))

    # If "Create a new category" was selected,
    # use the typed category name.
    if new_category == "__new__":
        if not new_category_name:
            return redirect(url_for("manage_shop"))

        new_category = new_category_name

        # Create the category if it does not already exist.
        if new_category not in usual_shop:
            usual_shop[new_category] = []

    # Make sure the destination category exists.
    if new_category not in usual_shop:
        return redirect(url_for("manage_shop"))

    old_position = usual_shop[old_category].index(old_item)

    # Nothing changed
    if old_item == new_item and old_category == new_category:
        return redirect(url_for("manage_shop"))

    # Changing only the item name
    if old_category == new_category:

        usual_shop[old_category][old_position] = new_item

    # Moving to another category
    else:

        usual_shop[old_category].remove(old_item)

        if new_item not in usual_shop[new_category]:
            usual_shop[new_category].append(new_item)

    save_usual_shop()

    return redirect(url_for("manage_shop"))


# ============================================================
# ADD ITEM TO TODAY'S LIST
# ============================================================

@app.route("/add-item", methods=["POST"])
def add_item():
    item = request.form.get("item", "").strip()
    category = request.form.get("category", "").strip()

    if item:

        # Always add the new item to today's list
        if item not in today_list:
            today_list.append(item)
            save_today_list()

        # If a category was selected, also remember the item
        # in the usual shop for future shopping trips
        if category in usual_shop:
            if item not in usual_shop[category]:
                usual_shop[category].append(item)
                save_usual_shop()

    return redirect(url_for("home"))


# ============================================================
# REMOVE ITEM FROM TODAY'S LIST
#
# Used before a trip starts (plain, online). Once a trip is
# under way, removal happens locally on the phone instead -
# see /api/complete-trip.
# ============================================================

@app.route("/remove/<path:item>", methods=["POST"])
def remove_item(item):
    if item in today_list:
        today_list.remove(item)
        save_today_list()

    if item in checked_items:
        checked_items.remove(item)
        save_checked_items()

    return redirect(url_for("home"))


# ============================================================
# COMPLETE A SHOPPING TRIP (called from the phone, in JSON)
#
# The entire trip - checking things off, removing things,
# timing - happens locally on the phone with no network
# needed. This is the one point where that local state is
# sent back to the server: once, at the end, as plain JSON.
# If the phone is offline when this is called, the JS side
# queues it and retries automatically once back online, so
# nothing is lost - it just arrives a little later.
# ============================================================

@app.route("/api/complete-trip", methods=["POST"])
def complete_trip():
    data = request.get_json(silent=True) or {}

    purchased_items = data.get("items") or []
    started_at = data.get("started_at")
    stopped_at = data.get("stopped_at")

    if not isinstance(purchased_items, list):
        purchased_items = []

    if purchased_items:
        trip = {
            "date": datetime.now().strftime("%d %B %Y"),
            "items": purchased_items
        }

        if started_at:
            trip["started_at"] = started_at

        if stopped_at:
            trip["stopped_at"] = stopped_at

        trip["overall_time"] = format_duration(started_at, stopped_at)

        shopping_history.insert(0, trip)
        save_shopping_history()

    # A completed trip always starts the next list fresh.
    today_list.clear()
    save_today_list()

    checked_items.clear()
    save_checked_items()

    return jsonify({"status": "ok"})


# ============================================================
# START THE APPLICATION
# ============================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        ssl_context=(
            "192.168.0.100+2.pem",
            "192.168.0.100+2-key.pem"
        )
    )
