from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import json
import os

app = Flask(__name__)
app.secret_key = "aws-ai-marketing-platform-2026-secret-key"

# 🔥 JSON STORAGE
USERS_FILE = 'users.json'
ADMINS_FILE = 'admins.json'
CAMPAIGNS_FILE = 'campaigns.json'

def load_json(filename, default={}):
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except:
            pass
    return default

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

users_db = load_json(USERS_FILE)
admins_db = load_json(ADMINS_FILE)
campaigns_db = load_json(CAMPAIGNS_FILE)

# 🔥 DEFAULT USERS
if "admin@company.com" not in admins_db:
    admins_db["admin@company.com"] = {
        "password": generate_password_hash("admin2026"),
        "name": "Platform Admin",
        "role": "admin"
    }
    save_json(ADMINS_FILE, admins_db)

if "john.doe@example.com" not in users_db:
    users_db["john.doe@example.com"] = {
        "password": generate_password_hash("password123"),
        "name": "Varsha",
        "role": "user"
    }
    save_json(USERS_FILE, users_db)

# ---------------- DECORATORS ---------------- #
def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first!", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapped

# ---------------- 🔥 ALL ROUTES - FIXED METHODS ---------------- #
@app.route("/")
@app.route("/index")
@app.route("/index.html")
def index():
    return render_template("index.html")

# 🔥 LOGIN - GET + POST
@app.route("/login", methods=['GET', 'POST'])
@app.route("/login.html", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return login_submit()  # Handle POST here
    return render_template("login.html")

# 🔥 SIGNUP - GET + POST  
@app.route("/signup", methods=['GET', 'POST'])
@app.route("/signup.html", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        return signup_submit()  # Handle POST here
    return render_template("signup.html")

# 🔥 HOME
@app.route("/home")
@app.route("/home.html")
@login_required
def home():
    user = users_db.get(session["user_id"], {})
    return render_template("home.html", user=user)

# 🔥 ABOUT
@app.route("/about")
@app.route("/about.html")
def about():
    return render_template("about.html")

# 🔥 ADMIN LOGIN - GET + POST
@app.route("/admin_login", methods=['GET', 'POST'])
@app.route("/admin_login.html", methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        return admin_login_submit()
    return render_template("admin_login.html")

# 🔥 ADMIN HOME
@app.route("/admin_home")
@app.route("/admin_home.html")
def admin_home():
    if session.get("role") != "admin":
        session["user_id"] = "admin@company.com"
        session["role"] = "admin"
    return render_template("admin_home.html", campaigns=campaigns_db, users=users_db)

# 🔥 DASHBOARD
@app.route("/dashboard")
@app.route("/dashboard.html")
@login_required
def dashboard():
    user_campaigns = [c for c in campaigns_db if c.get("user") == session["user_id"]]
    return render_template("dashboard.html", campaigns=user_campaigns)

# 🔥 CAMPAIGN
@app.route("/campaign")
@app.route("/campaign.html")
@login_required
def campaign():
    return render_template("campaign.html")

# 🔥 HISTORY
@app.route("/campaign_history")
@app.route("/campaign_history.html")
@login_required
def campaign_history():
    user_campaigns = [c for c in campaigns_db if c.get("user") == session["user_id"]]
    return render_template("campaign_history.html", campaigns=user_campaigns)

# 🔥 DIRECT ADMIN
@app.route("/login_to_dashboard")
@app.route("/admin_direct")
def direct_admin_login():
    session["user_id"] = "admin@company.com"
    session["role"] = "admin"
    return redirect(url_for("admin_home"))

# ---------------- 🔥 FORM HANDLERS - POST ONLY ---------------- #
@app.route("/api/login-submit", methods=['POST'])
def login_submit():
    email = request.form.get("email", "").lower()
    password = request.form.get("password", "")

    if email in users_db and check_password_hash(users_db[email]["password"], password):
        session["user_id"] = email
        session["role"] = "user"
        print(f"👤 LOGIN: {email}")
        return redirect(url_for("home"))

    if email in admins_db and check_password_hash(admins_db[email]["password"], password):
        session["user_id"] = email
        session["role"] = "admin"
        print(f"👑 ADMIN LOGIN: {email}")
        return redirect(url_for("admin_home"))

    flash("Invalid credentials!", "error")
    return redirect(url_for("login"))

@app.route("/api/signup-submit", methods=['POST'])
def signup_submit():
    email = request.form.get("signupEmail", "").lower()
    password = request.form.get("signupPassword", "")
    confirm = request.form.get("confirmPassword", "")

    if password != confirm:
        flash("Passwords don't match!", "error")
        return redirect(url_for("signup"))

    if email in users_db:
        flash("User already exists!", "error")
        return redirect(url_for("signup"))

    users_db[email] = {
        "password": generate_password_hash(password),
        "name": email.split("@")[0],
        "role": "user"
    }
    save_json(USERS_FILE, users_db)
    
    flash("Signup successful! Please login.", "success")
    return redirect(url_for("login"))

@app.route("/api/admin-login-submit", methods=['POST'])
def admin_login_submit():
    email = request.form.get("adminEmail", "").lower()
    password = request.form.get("adminPassword", "")

    if email in admins_db and check_password_hash(admins_db[email]["password"], password):
        session["user_id"] = email
        session["role"] = "admin"
        return redirect(url_for("admin_home"))

    flash("Invalid admin credentials!", "error")
    return redirect(url_for("admin_login"))

# 🔥 CAMPAIGN
@app.route("/api/generate-campaign", methods=['POST'])
@login_required
def generate_campaign():
    interest = request.form.get("userInterests", "")
    campaign = {
        "id": len(campaigns_db) + 1,
        "user": session["user_id"],
        "interest": interest,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "Active"
    }
    campaigns_db.insert(0, campaign)
    save_json(CAMPAIGNS_FILE, campaigns_db)
    return jsonify(campaign)

# 🔥 LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    print("🚀 FIXED - NO MORE 405 ERRORS!")
    print("👑 Admin: admin@company.com / admin2026")
    print("👤 User: john.doe@example.com / password123")
    app.run(debug=True, host='0.0.0.0', port=5000)
