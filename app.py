import os
import math
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from groq import Groq

# ==========================================
# 1. APPLICATION & CONFIGURATION SETUP
# ==========================================
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'astrotime-secret-key-2026')

# Database Setup (Supports SQLite locally and PostgreSQL on Render)
db_url = os.environ.get("DATABASE_URL", "sqlite:///local_astrolog.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Login Manager Initialization
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Groq AI Client Setup
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "gsk_YOUR_GROQ_API_KEY_HERE")
groq_client = Groq(api_key=GROQ_API_KEY)


# ==========================================
# 2. DATABASE MODELS
# ==========================================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class AnalysisLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    input_date = db.Column(db.String(20), nullable=False)
    input_time = db.Column(db.String(20), nullable=False)
    timezone_offset = db.Column(db.Float, nullable=False)
    julian_date = db.Column(db.Float)
    eot_minutes = db.Column(db.Float)
    solar_time = db.Column(db.String(10))
    sidereal_time = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Create Database Tables & Auto-Migrate
with app.app_context():
    db.create_all()
    # Auto-add missing user_id column if upgrading an existing SQLite database
    try:
        with db.engine.connect() as conn:
            conn.execute(db.text("ALTER TABLE analysis_log ADD COLUMN user_id INTEGER REFERENCES user(id);"))
            conn.commit()
    except Exception:
        pass  # Column already exists or table is newly created


# ==========================================
# 3. ASTRONOMICAL COMPUTATION LOGIC
# ==========================================
def calculate_astronomy_data(lat, lon, date_str, time_str, tz_offset):
    dt_local = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    day_of_year = dt_local.timetuple().tm_yday
    
    local_hours = dt_local.hour + (dt_local.minute / 60.0)
    utc_hours = (local_hours - tz_offset) % 24

    # Julian Date Calculation
    year, month, day = dt_local.year, dt_local.month, dt_local.day
    if month <= 2:
        year -= 1
        month += 12
    
    a = math.floor(year / 100)
    b = 2 - a + math.floor(a / 4)
    jd0 = math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + b - 1524.5
    julian_date = jd0 + (utc_hours / 24.0)

    # Equation of Time (EoT)
    b_rad = math.radians((360.0 / 365.0) * (day_of_year - 81))
    eot = 9.87 * math.sin(2 * b_rad) - 7.53 * math.cos(b_rad) - 1.5 * math.sin(b_rad)

    # Local Solar Time
    standard_meridian = 15.0 * tz_offset
    time_correction = 4.0 * (lon - standard_meridian) + eot
    solar_hours_decimal = (local_hours + (time_correction / 60.0)) % 24
    
    sh = int(solar_hours_decimal)
    sm = int((solar_hours_decimal - sh) * 60)
    solar_time = f"{sh:02d}:{sm:02d}"

    # Local Sidereal Time (LST)
    days_since_j2000 = julian_date - 2451545.0
    gmst = (18.697374558 + 24.06570982441908 * days_since_j2000) % 24
    lst_decimal = (gmst + (lon / 15.0)) % 24
    
    lh = int(lst_decimal)
    lm = int((lst_decimal - lh) * 60)
    sidereal_time = f"{lh:02d}:{lm:02d}"

    return {
        "julian_date": round(julian_date, 5),
        "eot": round(eot, 2),
        "solar_time": solar_time,
        "sidereal_time": sidereal_time
    }


# ==========================================
# 4. ROUTE CONTROLLERS
# ==========================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analysis')
def analysis():
    return render_template('analysis.html')

@app.route('/learn')
def learn():
    return render_template('learn.html')

@app.route('/ai-assistant')
def ai_assistant():
    return render_template('ai.html')

@app.route('/about')
def about():
    return render_template('about.html')


# ==========================================
# 5. USER AUTHENTICATION ROUTES
# ==========================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash('Username already taken!')
            return redirect(url_for('register'))

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect(url_for('index'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        
        flash('Invalid username or password')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


# ==========================================
# 6. API ENDPOINTS
# ==========================================
@app.route('/api/calculate', methods=['POST'])
def calculate():
    try:
        data = request.get_json()
        lat = float(data['latitude'])
        lon = float(data['longitude'])
        date_str = data['date']
        time_str = data['time']
        tz_offset = float(data['timezone'])

        results = calculate_astronomy_data(lat, lon, date_str, time_str, tz_offset)

        # Log into database
        user_id = current_user.id if current_user.is_authenticated else None
        log_entry = AnalysisLog(
            user_id=user_id,
            latitude=lat,
            longitude=lon,
            input_date=date_str,
            input_time=time_str,
            timezone_offset=tz_offset,
            julian_date=results['julian_date'],
            eot_minutes=results['eot'],
            solar_time=results['solar_time'],
            sidereal_time=results['sidereal_time']
        )
        db.session.add(log_entry)
        db.session.commit()

        return jsonify({"success": True, "results": results})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()

        if not user_message:
            return jsonify({"response": "Please enter a valid question."})

        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are AstroTime AI, an expert astronomical and geomatics co-pilot helping students and surveyors with solar time, sidereal drift, coordinate transformations, and field astronomical calculations."},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=1024
        )

        reply = completion.choices[0].message.content
        return jsonify({"response": reply})

    except Exception as e:
        return jsonify({"response": f"AI Connection Error: {str(e)}"}), 500


# ==========================================
# 7. MAIN EXECUTION
# ==========================================
if __name__ == '__main__':
    app.run(debug=True)