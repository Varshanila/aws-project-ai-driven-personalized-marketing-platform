from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
from dotenv import load_dotenv
import boto3, uuid, json, os

load_dotenv()

app = Flask(__name__)
app.secret_key = "aws-ai-marketing-platform-2026-secret-key"

# =========================================================
# 🔥 AWS CONFIG
# =========================================================
USE_AWS = True

try:
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    sns = boto3.client('sns', region_name='us-east-1')

    user_table = dynamodb.Table('UserTable')
    admin_table = dynamodb.Table('AdminTable')
    campaign_table = dynamodb.Table('CampaignsTable')

    SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:YOUR-ACCOUNT-ID:aws-ai-marketing-alerts'
except Exception as e:
    print("⚠️ AWS not available, using JSON storage")
    USE_AWS = False

# =========================================================
# 🔥 JSON FALLBACK STORAGE
# =========================================================
USERS_FILE = "users.json"
ADMINS_FILE = "admins.json"
CAMPAIGNS_FILE = "campaigns.json"

def load_json(file, default):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return default

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

users_db = load_json(USERS_FILE, {})
admins_db = load_json(ADMINS_FILE, {})
campaigns_db = load_json(CAMPAIGNS_FILE, [])

# Default Admin
if "admin@company.com" not in admins_db:
    admins_db["admin@company.com"] = {
        "password": generate_password_hash("admin2026"),
        "role": "admin"
    }
    save_json(ADMINS_FILE, admins_db)

# =========================================================
# 🔐 HELPERS
# =========================================================
def send_sns(subject, message):
    if USE_AWS:
        try:
            sns.publish(TopicArn=SNS_TOPIC_ARN, Subject=subject, Message=message)
        except:
            pass

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrap

# =========================================================
# 🌍 ROUTES (PAGES)
# =========================================================
@app.route("/")
@app.route("/index.html")
def index():
    return render_template("index.html")

@app.route("/about.html")
def about():
    return render_template("about.html")

@app.route("/login.html")
def login():
    return render_template("login.html")

@app.route("/signup.html")
def signup():
    return render_template("signup.html")

@app.route("/admin_login.html")
def admin_login():
    return render_template("admin_login.html")

@app.route("/home.html")
@login_required
def home():
    return render_template("home.html")

@app.route("/dashboard.html")
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route("/admin_home.html")
def admin_home():
    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))
    return render_template("admin_home.html", users=users_db, campaigns=campaigns_db)

# =========================================================
# 🔥 AUTH API
# =========================================================
@app.route("/api/signup-submit", methods=["POST"])
def signup_submit():
    email = request.form.get("signupEmail", "").lower()
    password = request.form.get("signupPassword", "")
    confirm = request.form.get("confirmPassword", "")

    if password != confirm:
        flash("Passwords do not match!")
        return redirect(url_for("signup"))

    if USE_AWS:
        if user_table.get_item(Key={"email": email}).get("Item"):
            flash("User already exists!")
            return redirect(url_for("signup"))

        user_table.put_item(Item={
            "email": email,
            "password": generate_password_hash(password),
            "created_at": datetime.now().isoformat()
        })
    else:
        if email in users_db:
            flash("User already exists!")
            return redirect(url_for("signup"))

        users_db[email] = {
            "password": generate_password_hash(password),
            "role": "user"
        }
        save_json(USERS_FILE, users_db)

    send_sns("🆕 SIGNUP", email)
    flash("Signup successful! Please login.")
    return redirect(url_for("login"))

@app.route("/api/login-submit", methods=["POST"])
def login_submit():
    email = request.form.get("email", "").lower()
    password = request.form.get("password", "")

    user = None
    if USE_AWS:
        user = user_table.get_item(Key={"email": email}).get("Item")
    else:
        user = users_db.get(email)

    if user and check_password_hash(user["password"], password):
        session["user_id"] = email
        session["role"] = "user"
        send_sns("👤 LOGIN", email)
        return redirect(url_for("home"))

    if email in admins_db and check_password_hash(admins_db[email]["password"], password):
        session["user_id"] = email
        session["role"] = "admin"
        return redirect(url_for("admin_home"))

    flash("Invalid credentials!")
    return redirect(url_for("login"))

@app.route("/api/admin-login-submit", methods=["POST"])
def admin_login_submit():
    email = request.form.get("adminEmail", "").lower()
    password = request.form.get("adminPassword", "")

    if email in admins_db and check_password_hash(admins_db[email]["password"], password):
        session["user_id"] = email
        session["role"] = "admin"
        return redirect(url_for("admin_home"))

    flash("Invalid admin credentials!")
    return redirect(url_for("admin_login"))

# =========================================================
# 🚪 LOGOUT
# =========================================================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# =========================================================
if __name__ == "__main__":
    print("🚀 MERGED APP RUNNING")
    print("👑 Admin: admin@company.com / admin2026")
    app.run(debug=True, host="0.0.0.0", port=5000)
