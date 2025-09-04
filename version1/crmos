from flask import Flask, render_template_string, request, redirect, url_for, flash, session
import sqlite3
import os
import re
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

# Configuration
DB_FILE = "contacts.db"
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")  # Change in production

# --- Database setup ---
def init_db():
    """Initialize the database with contacts and users tables"""
    new_db = not os.path.exists(DB_FILE)
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        if new_db:
            # Contacts table
            c.execute("""
                CREATE TABLE contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT,
                    address TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            c.execute("""
                CREATE TRIGGER IF NOT EXISTS update_contacts_timestamp 
                AFTER UPDATE ON contacts
                BEGIN
                    UPDATE contacts SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                END
            """)
            # Users table
            c.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# --- Auth Helpers ---
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

# --- Validation ---
def validate_name(name):
    return bool(name and len(name.strip()) >= 2)

def validate_phone(phone):
    if not phone:
        return True
    pattern = r"^[\d\s\-\+\(\)]{7,20}$"
    return re.match(pattern, phone) is not None

# --- Error Handlers ---
@app.errorhandler(404)
def not_found(error):
    return render_template_string(ERROR_TEMPLATE, error_code=404, error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template_string(ERROR_TEMPLATE, error_code=500, error_message="Internal server error"), 500

# --- Auth Routes ---
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        if len(username) < 3 or len(password) < 6:
            flash("Username must be ≥3 chars and password ≥6 chars", "error")
            return redirect(url_for("register"))
        pw_hash = generate_password_hash(password)
        try:
            with get_db_connection() as conn:
                conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, pw_hash))
                conn.commit()
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already exists", "error")
    return render_template_string(REG_TEMPLATE)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        with get_db_connection() as conn:
            user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Welcome back!", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid credentials", "error")
    return render_template_string(LOGIN_TEMPLATE)

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "success")
    return redirect(url_for("login"))

# --- Contact Routes ---
@app.route("/", methods=["GET"])
@login_required
def index():
    search = request.args.get("search", "").strip()
    try:
        with get_db_connection() as conn:
            if search:
                contacts = conn.execute(
                    "SELECT * FROM contacts WHERE name LIKE ? OR phone LIKE ? OR notes LIKE ? ORDER BY name",
                    (f"%{search}%", f"%{search}%", f"%{search}%"),
                ).fetchall()
            else:
                contacts = conn.execute("SELECT * FROM contacts ORDER BY name").fetchall()
        return render_template_string(TEMPLATE, contacts=contacts, search=search, username=session.get("username"))
    except sqlite3.Error:
        flash("Database error occurred", "error")
        return render_template_string(TEMPLATE, contacts=[], search=search, username=session.get("username"))

@app.route("/add", methods=["POST"])
@login_required
def add():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    address = request.form.get("address", "").strip()
    notes = request.form.get("notes", "").strip()

    if not validate_name(name):
        flash("Name is required and must be at least 2 characters", "error")
        return redirect(url_for("index"))
    if not validate_phone(phone):
        flash("Invalid phone number format", "error")
        return redirect(url_for("index"))

    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO contacts (name, phone, address, notes) VALUES (?, ?, ?, ?)",
                (name, phone, address, notes),
            )
            conn.commit()
        flash("Contact added successfully", "success")
    except sqlite3.Error:
        flash("Failed to add contact", "error")

    return redirect(url_for("index"))

@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    try:
        with get_db_connection() as conn:
            contact = conn.execute("SELECT * FROM contacts WHERE id = ?", (id,)).fetchone()
            if not contact:
                flash("Contact not found", "error")
                return redirect(url_for("index"))
            if request.method == "POST":
                name = request.form.get("name", "").strip()
                phone = request.form.get("phone", "").strip()
                address = request.form.get("address", "").strip()
                notes = request.form.get("notes", "").strip()

                if not validate_name(name):
                    flash("Name is required and must be at least 2 characters", "error")
                    return render_template_string(EDIT_TEMPLATE, contact=contact)
                if not validate_phone(phone):
                    flash("Invalid phone number format", "error")
                    return render_template_string(EDIT_TEMPLATE, contact=contact)

                conn.execute(
                    "UPDATE contacts SET name=?, phone=?, address=?, notes=? WHERE id=?",
                    (name, phone, address, notes, id),
                )
                conn.commit()
                flash("Contact updated successfully", "success")
                return redirect(url_for("index"))
        return render_template_string(EDIT_TEMPLATE, contact=contact)
    except sqlite3.Error:
        flash("Database error occurred", "error")
        return redirect(url_for("index"))

@app.route("/delete/<int:id>")
@login_required
def delete(id):
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM contacts WHERE id=?", (id,))
            conn.commit()
        flash("Contact deleted successfully", "success")
    except sqlite3.Error:
        flash("Failed to delete contact", "error")
    return redirect(url_for("index"))

# --- Templates ---
BASE_STYLE = """
<script src="https://cdn.tailwindcss.com"></script>
<style>
    .alert-success { @apply bg-green-800 text-green-100 p-3 rounded-md mb-4; }
    .alert-error { @apply bg-red-800 text-red-100 p-3 rounded-md mb-4; }
    .empty-state { @apply text-gray-500 text-center py-8; }
</style>
"""

LOGIN_TEMPLATE = BASE_STYLE + """
<!doctype html>
<html lang="en"><head><meta charset="UTF-8"><title>Login</title></head>
<body class="bg-gray-900 text-gray-100 min-h-screen flex items-center justify-center p-6">
<div class="w-full max-w-md bg-gray-800 p-6 rounded-lg shadow-lg">
<h1 class="text-3xl font-bold mb-6 text-center text-indigo-400">Login</h1>
{% with messages = get_flashed_messages(with_categories=true) %}
  {% for category, message in messages %}
    <div class="alert-{{ category }}">{{ message }}</div>
  {% endfor %}
{% endwith %}
<form method="post" class="grid gap-4">
  <input name="username" placeholder="Username" required class="p-3 rounded bg-gray-700 border border-gray-600">
  <input type="password" name="password" placeholder="Password" required class="p-3 rounded bg-gray-700 border border-gray-600">
  <button class="bg-indigo-600 hover:bg-indigo-500 p-3 rounded font-medium">Login</button>
</form>
<p class="text-center mt-4 text-gray-400">No account? <a href="{{ url_for('register') }}" class="text-indigo-400">Register</a></p>
</div></body></html>
"""

REG_TEMPLATE = BASE_STYLE + """
<!doctype html>
<html lang="en"><head><meta charset="UTF-8"><title>Register</title></head>
<body class="bg-gray-900 text-gray-100 min-h-screen flex items-center justify-center p-6">
<div class="w-full max-w-md bg-gray-800 p-6 rounded-lg shadow-lg">
<h1 class="text-3xl font-bold mb-6 text-center text-indigo-400">Register</h1>
{% with messages = get_flashed_messages(with_categories=true) %}
  {% for category, message in messages %}
    <div class="alert-{{ category }}">{{ message }}</div>
  {% endfor %}
{% endwith %}
<form method="post" class="grid gap-4">
  <input name="username" placeholder="Username" required class="p-3 rounded bg-gray-700 border border-gray-600">
  <input type="password" name="password" placeholder="Password" required class="p-3 rounded bg-gray-700 border border-gray-600">
  <button class="bg-indigo-600 hover:bg-indigo-500 p-3 rounded font-medium">Register</button>
</form>
<p class="text-center mt-4 text-gray-400">Already registered? <a href="{{ url_for('login') }}" class="text-indigo-400">Login</a></p>
</div></body></html>
"""

TEMPLATE = BASE_STYLE + """
<!doctype html>
<html lang="en"><head><meta charset="UTF-8"><title>CRM</title></head>
<body class="bg-gray-900 text-gray-100 min-h-screen p-6">
<div class="max-w-6xl mx-auto">
<div class="flex justify-between items-center mb-6">
  <h1 class="text-3xl font-bold text-indigo-400">Contacts CRM</h1>
  <div class="text-gray-300">Hello, {{ username }} | <a href="{{ url_for('logout') }}" class="text-red-400 hover:text-red-300">Logout</a></div>
</div>
{% with messages = get_flashed_messages(with_categories=true) %}
  {% for category, message in messages %}
    <div class="alert-{{ category }}">{{ message }}</div>
  {% endfor %}
{% endwith %}
<form method="get" class="mb-6 flex">
  <input type="text" name="search" value="{{ search }}" placeholder="Search contacts"
    class="flex-grow p-3 rounded-l bg-gray-800 border border-gray-700">
  <button class="p-3 bg-indigo-600 hover:bg-indigo-500 rounded-r">Search</button>
</form>
<div class="mb-6 p-4 bg-gray-800 rounded-lg shadow-md">
  <h2 class="text-xl font-semibold mb-4">Add Contact</h2>
  <form method="post" action="{{ url_for('add') }}" class="grid gap-3 md:grid-cols-2">
    <input name="name" placeholder="Name *" required class="p-3 rounded bg-gray-700 border border-gray-600">
    <input name="phone" placeholder="Phone" class="p-3 rounded bg-gray-700 border border-gray-600">
    <input name="address" placeholder="Address" class="p-3 rounded bg-gray-700 border border-gray-600">
    <input name="notes" placeholder="Notes" class="p-3 rounded bg-gray-700 border border-gray-600">
    <button class="col-span-2 bg-indigo-600 hover:bg-indigo-500 p-3 rounded">Add Contact</button>
  </form>
</div>
<h2 class="text-xl font-semibold mb-4">Contacts ({{ contacts|length }})</h2>
{% if contacts %}
<table class="min-w-full bg-gray-800 rounded-lg shadow-md">
<thead><tr class="bg-gray-700">
  <th class="p-3">Name</th><th class="p-3">Phone</th><th class="p-3">Address</th><th class="p-3">Notes</th><th class="p-3">Actions</th>
</tr></thead>
<tbody>
{% for c in contacts %}
<tr class="border-t border-gray-700 hover:bg-gray-750">
  <td class="p-3">{{ c['name'] }}</td>
  <td class="p-3">{{ c['phone'] }}</td>
  <td class="p-3">{{ c['address'] }}</td>
  <td class="p-3">{{ c['notes'] }}</td>
  <td class="p-3">
    <a href="{{ url_for('edit', id=c['id']) }}" class="text-indigo-400 hover:text-indigo-300">Edit</a> |
    <a href="{{ url_for('delete', id=c['id']) }}" class="text-red-400 hover:text-red-300" onclick="return confirm('Delete {{ c['name'] }}?')">Delete</a>
  </td>
</tr>
{% endfor %}
</tbody></table>
{% else %}
<p class="empty-state">No contacts found.</p>
{% endif %}
</div></body></html>
"""

EDIT_TEMPLATE = BASE_STYLE + """
<!doctype html>
<html lang="en"><head><meta charset="UTF-8"><title>Edit Contact</title></head>
<body class="bg-gray-900 text-gray-100 min-h-screen p-6 flex items-center justify-center">
<div class="max-w-lg w-full bg-gray-800 p-6 rounded-lg shadow-lg">
<h1 class="text-2xl font-bold mb-6 text-center text-indigo-400">Edit Contact</h1>
<form method="post" class="grid gap-4">
  <input name="name" value="{{ contact['name'] }}" required class="p-3 rounded bg-gray-700 border border-gray-600">
  <input name="phone" value="{{ contact['phone'] }}" class="p-3 rounded bg-gray-700 border border-gray-600">
  <input name="address" value="{{ contact['address'] }}" class="p-3 rounded bg-gray-700 border border-gray-600">
  <input name="notes" value="{{ contact['notes'] }}" class="p-3 rounded bg-gray-700 border border-gray-600">
  <div class="flex justify-between">
    <button class="bg-indigo-600 hover:bg-indigo-500 p-3 rounded">Save</button>
    <a href="{{ url_for('index') }}" class="bg-gray-700 hover:bg-gray-600 p-3 rounded">Cancel</a>
  </div>
</form>
</div></body></html>
"""

ERROR_TEMPLATE = BASE_STYLE + """
<!doctype html>
<html lang="en"><head><meta charset="UTF-8"><title>Error {{ error_code }}</title></head>
<body class="bg-gray-900 text-gray-100 min-h-screen flex items-center justify-center">
<div class="text-center">
  <h1 class="text-6xl font-bold text-indigo-400 mb-4">{{ error_code }}</h1>
  <p class="text-xl mb-6">{{ error_message }}</p>
  <a href="{{ url_for('index') }}" class="bg-indigo-600 hover:bg-indigo-500 p-3 rounded">Home</a>
</div></body></html>
"""

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
