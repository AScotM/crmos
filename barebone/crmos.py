from flask import Flask, render_template_string, request, redirect, url_for
import sqlite3
import os

DB_FILE = "contacts.db"
app = Flask(__name__)

# --- Database setup ---
def init_db():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                address TEXT,
                notes TEXT
            )
        """)
        conn.commit()
        conn.close()

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# --- Routes ---
@app.route("/", methods=["GET", "POST"])
def index():
    search = request.args.get("search", "")
    conn = get_db_connection()
    if search:
        contacts = conn.execute(
            "SELECT * FROM contacts WHERE name LIKE ? OR phone LIKE ? OR notes LIKE ?",
            (f"%{search}%", f"%{search}%", f"%{search}%")
        ).fetchall()
    else:
        contacts = conn.execute("SELECT * FROM contacts").fetchall()
    conn.close()
    return render_template_string(TEMPLATE, contacts=contacts, search=search)

@app.route("/add", methods=["POST"])
def add():
    name = request.form["name"]
    phone = request.form.get("phone", "")
    address = request.form.get("address", "")
    notes = request.form.get("notes", "")
    if name:
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO contacts (name, phone, address, notes) VALUES (?, ?, ?, ?)",
            (name, phone, address, notes)
        )
        conn.commit()
        conn.close()
    return redirect(url_for("index"))

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    conn = get_db_connection()
    contact = conn.execute("SELECT * FROM contacts WHERE id = ?", (id,)).fetchone()
    if not contact:
        conn.close()
        return "Contact not found", 404
    if request.method == "POST":
        name = request.form["name"]
        phone = request.form.get("phone", "")
        address = request.form.get("address", "")
        notes = request.form.get("notes", "")
        conn.execute(
            "UPDATE contacts SET name=?, phone=?, address=?, notes=? WHERE id=?",
            (name, phone, address, notes, id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("index"))
    conn.close()
    return render_template_string(EDIT_TEMPLATE, contact=contact)

@app.route("/delete/<int:id>")
def delete(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM contacts WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

# --- HTML Templates with TailwindCSS dark mode ---
TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Modern Dark CRM</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-gray-100 font-sans min-h-screen p-6">
<div class="max-w-4xl mx-auto">

<h1 class="text-4xl font-bold mb-6 text-center">Simple Modern CRM</h1>

<form method="get" class="mb-6 flex">
    <input type="text" name="search" value="{{search}}" placeholder="Search by name, phone, notes"
        class="flex-grow p-2 rounded-l-md bg-gray-800 border border-gray-700 text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500">
    <button type="submit" class="p-2 bg-indigo-600 hover:bg-indigo-500 rounded-r-md">Search</button>
    <a href="{{ url_for('index') }}" class="ml-2 p-2 bg-gray-700 hover:bg-gray-600 rounded-md">Clear</a>
</form>

<div class="mb-6 p-4 bg-gray-800 rounded-lg shadow-md">
<h2 class="text-2xl font-semibold mb-4">Add Contact</h2>
<form method="post" action="{{ url_for('add') }}" class="grid grid-cols-1 md:grid-cols-2 gap-4">
    <input type="text" name="name" placeholder="Name" required
        class="p-2 rounded-md bg-gray-700 border border-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500">
    <input type="text" name="phone" placeholder="Phone"
        class="p-2 rounded-md bg-gray-700 border border-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500">
    <input type="text" name="address" placeholder="Address"
        class="p-2 rounded-md bg-gray-700 border border-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500">
    <input type="text" name="notes" placeholder="Notes"
        class="p-2 rounded-md bg-gray-700 border border-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500">
    <button type="submit" class="col-span-2 bg-indigo-600 hover:bg-indigo-500 p-2 rounded-md">Add</button>
</form>
</div>

<h2 class="text-2xl font-semibold mb-4">Contacts</h2>
<div class="overflow-x-auto">
<table class="min-w-full bg-gray-800 rounded-lg overflow-hidden shadow-lg">
<tr class="bg-gray-700 text-left">
<th class="p-3">Name</th>
<th class="p-3">Phone</th>
<th class="p-3">Address</th>
<th class="p-3">Notes</th>
<th class="p-3">Actions</th>
</tr>
{% for c in contacts %}
<tr class="border-t border-gray-700 hover:bg-gray-700">
<td class="p-3">{{c['name']}}</td>
<td class="p-3">{{c['phone']}}</td>
<td class="p-3">{{c['address']}}</td>
<td class="p-3">{{c['notes']}}</td>
<td class="p-3 space-x-2">
    <a href="{{ url_for('edit', id=c['id']) }}" class="text-indigo-400 hover:text-indigo-300">Edit</a>
    <a href="{{ url_for('delete', id=c['id']) }}" class="text-red-400 hover:text-red-300"
       onclick="return confirm('Delete this contact?')">Delete</a>
</td>
</tr>
{% endfor %}
</table>
</div>
</div>
</body>
</html>
"""

EDIT_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Edit Contact</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-gray-100 font-sans min-h-screen p-6">
<div class="max-w-2xl mx-auto">

<h1 class="text-3xl font-bold mb-6 text-center">Edit Contact</h1>
<form method="post" class="grid grid-cols-1 gap-4 bg-gray-800 p-6 rounded-lg shadow-md">
    <input type="text" name="name" value="{{contact['name']}}" placeholder="Name" required
        class="p-2 rounded-md bg-gray-700 border border-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500">
    <input type="text" name="phone" value="{{contact['phone']}}" placeholder="Phone"
        class="p-2 rounded-md bg-gray-700 border border-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500">
    <input type="text" name="address" value="{{contact['address']}}" placeholder="Address"
        class="p-2 rounded-md bg-gray-700 border border-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500">
    <input type="text" name="notes" value="{{contact['notes']}}" placeholder="Notes"
        class="p-2 rounded-md bg-gray-700 border border-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500">
    <div class="flex justify-between">
        <button type="submit" class="bg-indigo-600 hover:bg-indigo-500 p-2 rounded-md">Save</button>
        <a href="{{ url_for('index') }}" class="bg-gray-700 hover:bg-gray-600 p-2 rounded-md">Cancel</a>
    </div>
</form>
</div>
</body>
</html>
"""

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
