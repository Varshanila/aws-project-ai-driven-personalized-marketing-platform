from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import boto3
import uuid
import os

# ---------------- BASIC APP SETUP ---------------- #
app = Flask(__name__)
app.secret_key = "aws-ai-marketing-platform-2026-secret-key"

AWS_REGION = "us-east-1"

# ---------------- AWS SETUP ---------------- #
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)

USER_TABLE = dynamodb.Table("UserTable")
ADMIN_TABLE = dynamodb.Table("AdminTable")
CAMPAIGN_TABLE = dynamodb.Table("CampaignsTable")

# ---------------- DECORATORS ---------------- #
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_email" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper

# ---------------- ROUTES (PAGES) ---------------- #
@app.route("/")
@app.route("/index")
@app.route("/index.html")
def index():
    return render_template("index.html")

@app.route("/login")
@app.route("/login.html")
def login():
    return render_template("login.html")

@app.route("/signup")
@app.route("/signup.html")
def signup():
    return render_template("signup.html")

@app.route("/about")
@app.route("/about.html")
def about():
    return render_template("about.html")

@app.route("/home")
@app.route("/home.html")
@login_required
def home():
    return render_template("home.html")

@app.route("/admin_login")
@app.route("/admin_login.html")
def admin_login():
    return render_template("admin_login.html")

@app.route("/admin_home")
@app.route("/admin_home.html")
@admin_required
def admin_home():
    users = USER_TABLE.scan().get("Items", [])
    campaigns = CAMPAIGN_TABLE.scan().get("Items", [])
    return render_template("admin_home.html", users=users, campaigns=campaigns)

@app.route("/dashboard")
@app.route("/dashboard.html")
@login_required
def dashboard():
    response = CAMPAIGN_TABLE.scan()
    campaigns = [c for c in response.get("Items", []) if c.get("user_email") == session["user_email"]]
    return render_template("dashboard.html", campaigns=campaigns)

@app.route("/campaign")
@app.route("/campaign.html")
@login_required
def campaign():
    return render_template("campaign.html")

# ---------------- FORM HANDLERS ---------------- #

# ✅ USER LOGIN (login.html)
@app.route("/api/login-submit", methods=["POST"])
def login_submit():
    email = request.form.get("email", "").lower()
    password = request.form.get("password", "")

    user = USER_TABLE.get_item(Key={"email": email}).get("Item")
    if user and check_password_hash(user["password"], password):
        session["user_email"] = email
        session["role"] = "user"
        return redirect(url_for("home"))

    admin = ADMIN_TABLE.get_item(Key={"email": email}).get("Item")
    if admin and check_password_hash(admin["password"], password):
        session["user_email"] = email
        session["role"] = "admin"
        return redirect(url_for("admin_home"))

    flash("Invalid credentials")
    return redirect(url_for("login"))

# ✅ USER SIGNUP (signup.html)
@app.route("/api/signup-submit", methods=["POST"])
def signup_submit():
    email = request.form.get("signupEmail", "").lower()
    password = request.form.get("signupPassword", "")
    confirm = request.form.get("confirmPassword", "")
    full_name = request.form.get("fullName", "")
    contact = request.form.get("contact", "")

    if password != confirm:
        flash("Passwords do not match")
        return redirect(url_for("signup"))

    if USER_TABLE.get_item(Key={"email": email}).get("Item"):
        flash("User already exists")
        return redirect(url_for("signup"))

    USER_TABLE.put_item(Item={
        "email": email,
        "password": generate_password_hash(password),
        "name": full_name,
        "contact": contact,
        "created_at": datetime.utcnow().isoformat()
    })

    flash("Signup successful. Please login.")
    return redirect(url_for("login"))

# ✅ ADMIN LOGIN (admin_login.html)
@app.route("/api/admin-login-submit", methods=["POST"])
def admin_login_submit():
    email = request.form.get("adminEmail", "").lower()
    password = request.form.get("adminPassword", "")

    admin = ADMIN_TABLE.get_item(Key={"email": email}).get("Item")
    if admin and check_password_hash(admin["password"], password):
        session["user_email"] = email
        session["role"] = "admin"
        return redirect(url_for("admin_home"))

    flash("Invalid admin credentials")
    return redirect(url_for("admin_login"))

# ✅ CREATE CAMPAIGN
@app.route("/api/generate-campaign", methods=["POST"])
@login_required
def generate_campaign():
    interest = request.form.get("userInterests", "")

    CAMPAIGN_TABLE.put_item(Item={
        "campaign_id": str(uuid.uuid4()),
        "user_email": session["user_email"],
        "interest": interest,
        "status": "Active",
        "created_at": datetime.utcnow().isoformat()
    })

    return jsonify({"status": "success"})

# ---------------- LOGOUT ---------------- #
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ---------------- RUN APP ---------------- #
if __name__ == "__main__":
    print("🚀 FINAL MERGED APP RUNNING")
    print("👑 Admin login from DynamoDB")
    print("👤 User signup/login stored in DynamoDB")
    app.run(host="0.0.0.0", port=5000, debug=True)
