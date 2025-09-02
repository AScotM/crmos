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
        contacts = conn.execute("SELECT * FROM contacts WHERE name LIKE ? OR phone LIKE ? OR notes LIKE ?",
                                (f"%{search}%", f"%{search}%", f"%{search}%")).fetchall()
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
        conn.execute("INSERT INTO contacts (name, phone, address, notes) VALUES (?, ?, ?, ?)",
                     (name, phone, address, notes))
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
        conn.execute("UPDATE contacts SET name=?, phone=?, address=?, notes=? WHERE id=?",
                     (name, phone, address, notes, id))
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

# --- HTML Templates ---
TEMPLATE = """
<!doctype html>
<title>Simple CRM</title>
<h1>Simple CRM</h1>
<form method="get">
    <input type="text" name="search" value="{{search}}" placeholder="Search by name, phone, notes">
    <input type="submit" value="Search">
    <a href="{{ url_for('index') }}">Clear</a>
</form>

<h2>Add Contact</h2>
<form method="post" action="{{ url_for('add') }}">
    Name: <input type="text" name="name" required>
    Phone: <input type="text" name="phone">
    Address: <input type="text" name="address">
    Notes: <input type="text" name="notes">
    <input type="submit" value="Add">
</form>

<h2>Contacts</h2>
<table border="1" cellpadding="5" cellspacing="0">
<tr><th>Name</th><th>Phone</th><th>Address</th><th>Notes</th><th>Actions</th></tr>
{% for c in contacts %}
<tr>
    <td>{{c['name']}}</td>
    <td>{{c['phone']}}</td>
    <td>{{c['address']}}</td>
    <td>{{c['notes']}}</td>
    <td>
        <a href="{{ url_for('edit', id=c['id']) }}">Edit</a> |
        <a href="{{ url_for('delete', id=c['id']) }}" onclick="return confirm('Delete this contact?')">Delete</a>
    </td>
</tr>
{% endfor %}
</table>
"""

EDIT_TEMPLATE = """
<!doctype html>
<title>Edit Contact</title>
<h1>Edit Contact</h1>
<form method="post">
    Name: <input type="text" name="name" value="{{contact['name']}}" required><br>
    Phone: <input type="text" name="phone" value="{{contact['phone']}}"><br>
    Address: <input type="text" name="address" value="{{contact['address']}}"><br>
    Notes: <input type="text" name="notes" value="{{contact['notes']}}"><br>
    <input type="submit" value="Save">
    <a href="{{ url_for('index') }}">Cancel</a>
</form>
"""

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
