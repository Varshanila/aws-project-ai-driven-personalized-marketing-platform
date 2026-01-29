from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import boto3
import uuid
import logging

app = Flask(__name__)
app.secret_key = "aws-ai-marketing-platform-2026-secret-key"

# 🔥 AWS - UPDATE YOUR ARN!
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
sns = boto3.client('sns', region_name='us-east-1')

user_table = dynamodb.Table('UserTable')
admin_table = dynamodb.Table('AdminTable')
campaign_table = dynamodb.Table('CampaignsTable')

SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:YOUR-REAL-ACCOUNT-ID:aws-ai-marketing-alerts'

def send_sns(subject, message):
    try:
        sns.publish(TopicArn=SNS_TOPIC_ARN, Subject=subject, Message=message)
        print(f"✅ SNS: {subject}")
    except:
        print("❌ SNS failed")

# 🔥 DECORATORS
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# 🔥 ROUTES
@app.route("/")
@app.route("/index.html")
def index():
    return render_template("index.html")

@app.route("/about")
@app.route("/about.html")
def about():
    return render_template("about.html")

# 🔥 SIGNUP - FIXED
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email", "").lower()
        name = request.form.get("name", "")
        password = request.form.get("password", "")
        
        if not all([email, name, password]):
            flash("All fields required!")
            return render_template("signup.html")
        
        try:
            # Check if exists
            response = user_table.get_item(Key={'email': email})
            if response.get('Item'):
                flash("User exists!")
                return render_template("signup.html")
            
            # ✅ HASH PASSWORD
            user_table.put_item(Item={
                'email': email,
                'name': name,
                'password': generate_password_hash(password),
                'created_at': datetime.now().isoformat()
            })
            
            send_sns("🆕 SIGNUP", f"{email} registered")
            flash("Signup success!")
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"Error: {e}")
    
    return render_template("signup.html")

# 🔥 LOGIN - FIXED VALIDATION
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").lower()
        password = request.form.get("password", "")
        
        try:
            response = user_table.get_item(Key={'email': email})
            user = response.get('Item')
            
            # ✅ PROPER PASSWORD CHECK
            if user and check_password_hash(user['password'], password):
                session["user"] = email
                session["user_name"] = user.get('name', '')
                
                user_table.update_item(
                    Key={'email': email},
                    UpdateExpression="SET last_login = :t",
                    ExpressionAttributeValues={":t": datetime.now().isoformat()}
                )
                
                send_sns("👤 LOGIN", f"{email} logged in")
                return redirect(url_for("home"))
            else:
                flash("Invalid credentials!")
        except Exception as e:
            flash(f"Login error: {e}")
    
    return render_template("login.html")

@app.route("/home")
@login_required
def home():
    try:
        response = user_table.get_item(Key={'email': session['user']})
        user = response.get('Item', {})
    except:
        user = {}
    return render_template("home.html", user=user)

# 🔥 ADMIN LOGIN - FIXED
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email", "").lower()
        password = request.form.get("password", "")
        
        try:
            response = admin_table.get_item(Key={'email': email})
            admin = response.get('Item')
            
            if admin and check_password_hash(admin['password'], password):
                session["admin"] = email
                send_sns("👑 ADMIN", f"{email} logged in")
                return redirect(url_for("admin_home"))
            else:
                flash("Invalid admin credentials!")
        except Exception as e:
            flash(f"Error: {e}")
    
    return render_template("admin_login.html")

@app.route("/admin_home")
def admin_home():
    if "admin" not in session:
        return redirect(url_for("admin_login"))
    
    try:
        users = user_table.scan()['Items'] or []
        campaigns = campaign_table.scan()['Items'] or []
    except:
        users = campaigns = []
    
    return render_template("admin_home.html", users=users, campaigns=campaigns)

@app.route("/campaign")
@login_required
def campaign():
    return render_template("campaign.html")

@app.route("/add_campaign", methods=["POST"])
@login_required
def add_campaign():
    try:
        campaign_id = str(uuid.uuid4())
        campaign_table.put_item(Item={
            'campaign_id': campaign_id,
            'title': request.form.get("title", ""),
            'user': session['user'],
            'created_at': datetime.now().isoformat()
        })
        send_sns("📢 CAMPAIGN", f"Campaign created by {session['user']}")
        flash("Campaign created!")
    except Exception as e:
        flash(f"Error: {e}")
    return redirect(url_for("campaign"))

@app.route("/order", methods=["POST"])
@login_required
def order():
    try:
        order_id = str(uuid.uuid4())
        campaign_table.put_item(Item={
            'campaign_id': order_id,
            'type': 'order',
            'product': request.form.get("product", ""),
            'user': session['user'],
            'time': datetime.now().isoformat()
        })
        send_sns("🛒 ORDER", f"Order by {session['user']}")
        flash("Order placed!")
    except Exception as e:
        flash(f"Error: {e}")
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    print("🚀 AWS EC2 DEPLOYMENT READY!")
    print("⚠️ UPDATE SNS_TOPIC_ARN line 27!")
    print("👑 Admin: admin@company.com / admin2026")
    app.run(host="0.0.0.0", port=5000, debug=True)  # ✅ Fixed port
