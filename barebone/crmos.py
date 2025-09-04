from flask import Flask, render_template_string, request, redirect, url_for, flash
import sqlite3
import os
import re
from functools import wraps

# Configuration
DB_FILE = "contacts.db"
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')  # Change in production

# --- Database setup ---
def init_db():
    """Initialize the database with contacts table"""
    if not os.path.exists(DB_FILE):
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
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
            # Create trigger to update timestamp on row update
            c.execute("""
                CREATE TRIGGER IF NOT EXISTS update_contacts_timestamp 
                AFTER UPDATE ON contacts
                BEGIN
                    UPDATE contacts SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                END
            """)
            conn.commit()

def get_db_connection():
    """Get database connection with row factory"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# --- Validation functions ---
def validate_name(name):
    """Validate contact name"""
    if not name or len(name.strip()) < 2:
        return False
    return True

def validate_phone(phone):
    """Validate phone number format"""
    if not phone:
        return True
    # Simple phone validation pattern
    pattern = r'^[\d\s\-\+\(\)]{10,20}$'
    return re.match(pattern, phone) is not None

# --- Error handlers ---
@app.errorhandler(404)
def not_found(error):
    return render_template_string(ERROR_TEMPLATE, 
                                 error_code=404, 
                                 error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template_string(ERROR_TEMPLATE, 
                                 error_code=500, 
                                 error_message="Internal server error"), 500

# --- Routes ---
@app.route("/", methods=["GET", "POST"])
def index():
    """Main page with contact list and search"""
    search = request.args.get("search", "").strip()
    try:
        with get_db_connection() as conn:
            if search:
                contacts = conn.execute(
                    "SELECT * FROM contacts WHERE name LIKE ? OR phone LIKE ? OR notes LIKE ? ORDER BY name",
                    (f"%{search}%", f"%{search}%", f"%{search}%")
                ).fetchall()
            else:
                contacts = conn.execute("SELECT * FROM contacts ORDER BY name").fetchall()
        return render_template_string(TEMPLATE, contacts=contacts, search=search)
    except sqlite3.Error as e:
        flash("Database error occurred", "error")
        return render_template_string(TEMPLATE, contacts=[], search=search)

@app.route("/add", methods=["POST"])
def add():
    """Add a new contact"""
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    address = request.form.get("address", "").strip()
    notes = request.form.get("notes", "").strip()
    
    # Validate inputs
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
                (name, phone, address, notes)
            )
            conn.commit()
        flash("Contact added successfully", "success")
    except sqlite3.Error as e:
        flash("Failed to add contact", "error")
    
    return redirect(url_for("index"))

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    """Edit an existing contact"""
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
                
                # Validate inputs
                if not validate_name(name):
                    flash("Name is required and must be at least 2 characters", "error")
                    return render_template_string(EDIT_TEMPLATE, contact=contact)
                
                if not validate_phone(phone):
                    flash("Invalid phone number format", "error")
                    return render_template_string(EDIT_TEMPLATE, contact=contact)
                
                conn.execute(
                    "UPDATE contacts SET name=?, phone=?, address=?, notes=? WHERE id=?",
                    (name, phone, address, notes, id)
                )
                conn.commit()
                flash("Contact updated successfully", "success")
                return redirect(url_for("index"))
                
        return render_template_string(EDIT_TEMPLATE, contact=contact)
        
    except sqlite3.Error as e:
        flash("Database error occurred", "error")
        return redirect(url_for("index"))

@app.route("/delete/<int:id>")
def delete(id):
    """Delete a contact"""
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM contacts WHERE id=?", (id,))
            conn.commit()
        flash("Contact deleted successfully", "success")
    except sqlite3.Error as e:
        flash("Failed to delete contact", "error")
    
    return redirect(url_for("index"))

# --- HTML Templates ---
BASE_STYLE = """
<script src="https://cdn.tailwindcss.com"></script>
<style>
    .alert-success {
        @apply bg-green-800 text-green-100 p-3 rounded-md mb-4;
    }
    .alert-error {
        @apply bg-red-800 text-red-100 p-3 rounded-md mb-4;
    }
    .empty-state {
        @apply text-gray-500 text-center py-8;
    }
</style>
"""

TEMPLATE = BASE_STYLE + """
<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Modern Dark CRM</title>
</head>
<body class="bg-gray-900 text-gray-100 font-sans min-h-screen p-6">
<div class="max-w-6xl mx-auto">

<h1 class="text-4xl font-bold mb-6 text-center text-indigo-400">Simple Modern CRM</h1>

<!-- Flash messages -->
{% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
        <div class="mb-6">
            {% for category, message in messages %}
                <div class="alert-{{ category }}">{{ message }}</div>
            {% endfor %}
        </div>
    {% endif %}
{% endwith %}

<!-- Search form -->
<form method="get" class="mb-6 flex">
    <input type="text" name="search" value="{{ search }}" placeholder="Search by name, phone, notes"
        class="flex-grow p-3 rounded-l-md bg-gray-800 border border-gray-700 text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500">
    <button type="submit" class="p-3 bg-indigo-600 hover:bg-indigo-500 rounded-r-md">Search</button>
    <a href="{{ url_for('index') }}" class="ml-2 p-3 bg-gray-700 hover:bg-gray-600 rounded-md">Clear</a>
</form>

<!-- Add contact form -->
<div class="mb-6 p-4 bg-gray-800 rounded-lg shadow-md">
<h2 class="text-2xl font-semibold mb-4">Add Contact</h2>
<form method="post" action="{{ url_for('add') }}" class="grid grid-cols-1 md:grid-cols-2 gap-4">
    <input type="text" name="name" placeholder="Name *" required
        class="p-3 rounded-md bg-gray-700 border border-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500">
    <input type="text" name="phone" placeholder="Phone"
        class="p-3 rounded-md bg-gray-700 border border-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500">
    <input type="text" name="address" placeholder="Address"
        class="p-3 rounded-md bg-gray-700 border border-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500">
    <input type="text" name="notes" placeholder="Notes"
        class="p-3 rounded-md bg-gray-700 border border-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500">
    <button type="submit" class="col-span-2 bg-indigo-600 hover:bg-indigo-500 p-3 rounded-md font-medium">Add Contact</button>
</form>
</div>

<!-- Contacts list -->
<h2 class="text-2xl font-semibold mb-4">Contacts ({{ contacts|length }})</h2>
{% if contacts %}
<div class="overflow-x-auto rounded-lg shadow-lg">
<table class="min-w-full bg-gray-800">
<thead>
<tr class="bg-gray-700 text-left">
<th class="p-4">Name</th>
<th class="p-4">Phone</th>
<th class="p-4">Address</th>
<th class="p-4">Notes</th>
<th class="p-4">Actions</th>
</tr>
</thead>
<tbody>
{% for c in contacts %}
<tr class="border-t border-gray-700 hover:bg-gray-750">
<td class="p-4 font-medium">{{ c['name'] }}</td>
<td class="p-4">{{ c['phone'] }}</td>
<td class="p-4">{{ c['address'] }}</td>
<td class="p-4">{{ c['notes'] }}</td>
<td class="p-4 space-x-3">
    <a href="{{ url_for('edit', id=c['id']) }}" class="text-indigo-400 hover:text-indigo-300">Edit</a>
    <a href="{{ url_for('delete', id=c['id']) }}" class="text-red-400 hover:text-red-300"
       onclick="return confirm('Are you sure you want to delete {{ c['name'] }}?')">Delete</a>
</td>
</tr>
{% endfor %}
</tbody>
</table>
</div>
{% else %}
<div class="empty-state bg-gray-800 rounded-lg p-8">
    <p>No contacts found. {% if search %}Try a different search term.{% else %}Add your first contact above.{% endif %}</p>
</div>
{% endif %}

</div>
</body>
</html>
"""

EDIT_TEMPLATE = BASE_STYLE + """
<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Edit Contact</title>
</head>
<body class="bg-gray-900 text-gray-100 font-sans min-h-screen p-6">
<div class="max-w-2xl mx-auto">

<h1 class="text-3xl font-bold mb-6 text-center text-indigo-400">Edit Contact</h1>

<!-- Flash messages -->
{% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
        <div class="mb-6">
            {% for category, message in messages %}
                <div class="alert-{{ category }}">{{ message }}</div>
            {% endfor %}
        </div>
    {% endif %}
{% endwith %}

<form method="post" class="grid grid-cols-1 gap-4 bg-gray-800 p-6 rounded-lg shadow-md">
    <input type="text" name="name" value="{{ contact['name'] }}" placeholder="Name *" required
        class="p-3 rounded-md bg-gray-700 border border-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500">
    <input type="text" name="phone" value="{{ contact['phone'] }}" placeholder="Phone"
        class="p-3 rounded-md bg-gray-700 border border-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500">
    <input type="text" name="address" value="{{ contact['address'] }}" placeholder="Address"
        class="p-3 rounded-md bg-gray-700 border border-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500">
    <input type="text" name="notes" value="{{ contact['notes'] }}" placeholder="Notes"
        class="p-3 rounded-md bg-gray-700 border border-gray-600 focus:outline-none focus:ring-2 focus:ring-indigo-500">
    <div class="flex justify-between mt-4">
        <button type="submit" class="bg-indigo-600 hover:bg-indigo-500 p-3 rounded-md font-medium">Save Changes</button>
        <a href="{{ url_for('index') }}" class="bg-gray-700 hover:bg-gray-600 p-3 rounded-md font-medium">Cancel</a>
    </div>
</form>

</div>
</body>
</html>
"""

ERROR_TEMPLATE = BASE_STYLE + """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Error {{ error_code }}</title>
</head>
<body class="bg-gray-900 text-gray-100 font-sans min-h-screen flex items-center justify-center p-6">
    <div class="text-center">
        <h1 class="text-6xl font-bold text-indigo-400 mb-4">{{ error_code }}</h1>
        <p class="text-xl mb-6">{{ error_message }}</p>
        <a href="{{ url_for('index') }}" class="bg-indigo-600 hover:bg-indigo-500 p-3 rounded-md font-medium">
            Return to Home
        </a>
    </div>
</body>
</html>
"""

if __name__ == "__main__":
    init_db()
    # Use environment variables for configuration in production
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    
    app.run(debug=debug_mode, host=host, port=port)
