from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
import re
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect, CSRFError

# Configuration
DB_FILE = "contacts.db"
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")  # Change in production

# Initialize CSRF protection
csrf = CSRFProtect(app)

# --- Database setup ---
def init_db():
    """Initialize the database with contacts and users tables"""
    new_db = not os.path.exists(DB_FILE)
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        if new_db:
            # Users table
            c.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Contacts table with user association
            c.execute("""
                CREATE TABLE contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    phone TEXT,
                    email TEXT,
                    address TEXT,
                    notes TEXT,
                    category TEXT DEFAULT 'General',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes for better performance
            c.execute("CREATE INDEX idx_contacts_user_id ON contacts(user_id)")
            c.execute("CREATE INDEX idx_contacts_name ON contacts(name)")
            c.execute("CREATE INDEX idx_contacts_category ON contacts(category)")
            
            # Timestamp update trigger
            c.execute("""
                CREATE TRIGGER IF NOT EXISTS update_contacts_timestamp 
                AFTER UPDATE ON contacts
                BEGIN
                    UPDATE contacts SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                END
            """)
            
            # Categories table for better organization
            c.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    color TEXT DEFAULT '#3B82F6',
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)
            
            # Insert default categories
            default_categories = [
                (1, 'General', '#3B82F6'),
                (1, 'Family', '#EF4444'),
                (1, 'Work', '#10B981'),
                (1, 'Friends', '#F59E0B')
            ]
            
            c.executemany(
                "INSERT INTO categories (user_id, name, color) VALUES (?, ?, ?)",
                default_categories
            )
            
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

def validate_email(email):
    if not email:
        return True
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None

# --- Pagination ---
def get_pagination(page, per_page=10):
    return (page - 1) * per_page, per_page

# --- Error Handlers ---
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error_code=404, error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error_code=500, error_message="Internal server error"), 500

@app.errorhandler(CSRFError)
def handle_csrf_error(error):
    flash('CSRF token error. Please try again.', 'error')
    return redirect(request.referrer or url_for('index'))

# --- Auth Routes ---
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()
        
        if len(username) < 3:
            flash("Username must be at least 3 characters", "error")
            return render_template('register.html')
            
        if len(password) < 6:
            flash("Password must be at least 6 characters", "error")
            return render_template('register.html')
            
        pw_hash = generate_password_hash(password)
        try:
            with get_db_connection() as conn:
                cursor = conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, pw_hash))
                user_id = cursor.lastrowid
                
                # Create default categories for the new user
                default_categories = [
                    (user_id, 'General', '#3B82F6'),
                    (user_id, 'Family', '#EF4444'),
                    (user_id, 'Work', '#10B981'),
                    (user_id, 'Friends', '#F59E0B')
                ]
                
                conn.executemany(
                    "INSERT INTO categories (user_id, name, color) VALUES (?, ?, ?)",
                    default_categories
                )
                
                conn.commit()
                
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already exists", "error")
    
    return render_template('register.html')

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
    
    return render_template('login.html')

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
    category_filter = request.args.get("category", "").strip()
    page = request.args.get('page', 1, type=int)
    
    try:
        offset, per_page = get_pagination(page, 10)
        
        with get_db_connection() as conn:
            # Get user's categories
            categories = conn.execute(
                "SELECT * FROM categories WHERE user_id = ? ORDER BY name", 
                (session["user_id"],)
            ).fetchall()
            
            # Build query based on filters
            query = "SELECT * FROM contacts WHERE user_id = ?"
            params = [session["user_id"]]
            
            if search:
                query += " AND (name LIKE ? OR phone LIKE ? OR email LIKE ? OR notes LIKE ?)"
                search_param = f"%{search}%"
                params.extend([search_param, search_param, search_param, search_param])
            
            if category_filter:
                query += " AND category = ?"
                params.append(category_filter)
            
            query += " ORDER BY name LIMIT ? OFFSET ?"
            params.extend([per_page, offset])
            
            contacts = conn.execute(query, params).fetchall()
            
            # Get total count for pagination
            count_query = "SELECT COUNT(*) as total FROM contacts WHERE user_id = ?"
            count_params = [session["user_id"]]
            
            if search:
                count_query += " AND (name LIKE ? OR phone LIKE ? OR email LIKE ? OR notes LIKE ?)"
                search_param = f"%{search}%"
                count_params.extend([search_param, search_param, search_param, search_param])
            
            if category_filter:
                count_query += " AND category = ?"
                count_params.append(category_filter)
            
            total = conn.execute(count_query, count_params).fetchone()["total"]
            
        total_pages = (total + per_page - 1) // per_page
        
        return render_template(
            'index.html', 
            contacts=contacts, 
            categories=categories,
            search=search, 
            category_filter=category_filter,
            username=session.get("username"),
            page=page,
            total_pages=total_pages
        )
    except sqlite3.Error:
        flash("Database error occurred", "error")
        return render_template('index.html', contacts=[], search=search, username=session.get("username"))

@app.route("/add", methods=["POST"])
@login_required
def add():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    address = request.form.get("address", "").strip()
    notes = request.form.get("notes", "").strip()
    category = request.form.get("category", "General").strip()

    if not validate_name(name):
        flash("Name is required and must be at least 2 characters", "error")
        return redirect(url_for("index"))
    
    if not validate_phone(phone):
        flash("Invalid phone number format", "error")
        return redirect(url_for("index"))
    
    if not validate_email(email):
        flash("Invalid email format", "error")
        return redirect(url_for("index"))

    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO contacts (user_id, name, phone, email, address, notes, category) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (session["user_id"], name, phone, email, address, notes, category),
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
            # Verify the contact belongs to the current user
            contact = conn.execute(
                "SELECT * FROM contacts WHERE id = ? AND user_id = ?", 
                (id, session["user_id"])
            ).fetchone()
            
            if not contact:
                flash("Contact not found", "error")
                return redirect(url_for("index"))
            
            # Get user's categories
            categories = conn.execute(
                "SELECT * FROM categories WHERE user_id = ? ORDER BY name", 
                (session["user_id"],)
            ).fetchall()
            
            if request.method == "POST":
                name = request.form.get("name", "").strip()
                phone = request.form.get("phone", "").strip()
                email = request.form.get("email", "").strip()
                address = request.form.get("address", "").strip()
                notes = request.form.get("notes", "").strip()
                category = request.form.get("category", "General").strip()

                if not validate_name(name):
                    flash("Name is required and must be at least 2 characters", "error")
                    return render_template('edit.html', contact=contact, categories=categories)
                
                if not validate_phone(phone):
                    flash("Invalid phone number format", "error")
                    return render_template('edit.html', contact=contact, categories=categories)
                
                if not validate_email(email):
                    flash("Invalid email format", "error")
                    return render_template('edit.html', contact=contact, categories=categories)

                conn.execute(
                    "UPDATE contacts SET name=?, phone=?, email=?, address=?, notes=?, category=? WHERE id=? AND user_id=?",
                    (name, phone, email, address, notes, category, id, session["user_id"]),
                )
                conn.commit()
                flash("Contact updated successfully", "success")
                return redirect(url_for("index"))
        
        return render_template('edit.html', contact=contact, categories=categories)
    except sqlite3.Error:
        flash("Database error occurred", "error")
        return redirect(url_for("index"))

@app.route("/delete/<int:id>")
@login_required
def delete(id):
    try:
        with get_db_connection() as conn:
            # Verify the contact belongs to the current user before deleting
            result = conn.execute(
                "DELETE FROM contacts WHERE id=? AND user_id=?", 
                (id, session["user_id"])
            )
            
            if result.rowcount == 0:
                flash("Contact not found or you don't have permission to delete it", "error")
            else:
                conn.commit()
                flash("Contact deleted successfully", "success")
                
    except sqlite3.Error:
        flash("Failed to delete contact", "error")
    
    return redirect(url_for("index"))

# --- Category Management ---
@app.route("/categories")
@login_required
def categories():
    try:
        with get_db_connection() as conn:
            categories = conn.execute(
                "SELECT * FROM categories WHERE user_id = ? ORDER BY name", 
                (session["user_id"],)
            ).fetchall()
            
        return render_template('categories.html', categories=categories)
    except sqlite3.Error:
        flash("Database error occurred", "error")
        return render_template('categories.html', categories=[])

@app.route("/add_category", methods=["POST"])
@login_required
def add_category():
    name = request.form.get("name", "").strip()
    color = request.form.get("color", "#3B82F6").strip()
    
    if not name:
        flash("Category name is required", "error")
        return redirect(url_for("categories"))
    
    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO categories (user_id, name, color) VALUES (?, ?, ?)",
                (session["user_id"], name, color),
            )
            conn.commit()
        flash("Category added successfully", "success")
    except sqlite3.IntegrityError:
        flash("Category already exists", "error")
    except sqlite3.Error:
        flash("Failed to add category", "error")
    
    return redirect(url_for("categories"))

@app.route("/delete_category/<int:id>")
@login_required
def delete_category(id):
    try:
        with get_db_connection() as conn:
            # Check if category is in use
            in_use = conn.execute(
                "SELECT COUNT(*) as count FROM contacts WHERE category = (SELECT name FROM categories WHERE id = ? AND user_id = ?) AND user_id = ?",
                (id, session["user_id"], session["user_id"])
            ).fetchone()["count"]
            
            if in_use > 0:
                flash("Cannot delete category that is in use by contacts", "error")
                return redirect(url_for("categories"))
            
            # Don't allow deletion of default categories
            default_categories = ['General', 'Family', 'Work', 'Friends']
            category = conn.execute(
                "SELECT name FROM categories WHERE id = ? AND user_id = ?",
                (id, session["user_id"])
            ).fetchone()
            
            if category and category["name"] in default_categories:
                flash("Cannot delete default categories", "error")
                return redirect(url_for("categories"))
            
            # Delete the category
            result = conn.execute(
                "DELETE FROM categories WHERE id=? AND user_id=?", 
                (id, session["user_id"])
            )
            
            if result.rowcount == 0:
                flash("Category not found", "error")
            else:
                conn.commit()
                flash("Category deleted successfully", "success")
                
    except sqlite3.Error:
        flash("Failed to delete category", "error")
    
    return redirect(url_for("categories"))

# --- Export Route ---
@app.route("/export")
@login_required
def export_contacts():
    try:
        with get_db_connection() as conn:
            contacts = conn.execute(
                "SELECT name, phone, email, address, notes, category FROM contacts WHERE user_id = ? ORDER BY name",
                (session["user_id"],)
            ).fetchall()
        
        # Generate CSV content
        csv_content = "Name,Phone,Email,Address,Notes,Category\n"
        for contact in contacts:
            csv_content += f'"{contact["name"]}","{contact["phone"] or ""}","{contact["email"] or ""}","{contact["address"] or ""}","{contact["notes"] or ""}","{contact["category"] or ""}"\n'
        
        # Return as downloadable file
        from flask import Response
        return Response(
            csv_content,
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=my_contacts.csv"}
        )
    except sqlite3.Error:
        flash("Failed to export contacts", "error")
        return redirect(url_for("index"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
