from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

# -------------------------------------------------------------------
# 🗄️ DATABASE CONFIGURATION
# -------------------------------------------------------------------
# Configures a local SQLite database file named 'astro_data.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///astro_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define a Data Model structure to save your analysis inputs/outputs
class AnalysisLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    date_string = db.Column(db.String(50), nullable=False)
    time_string = db.Column(db.String(50), nullable=False)
    mean_solar = db.Column(db.String(50), nullable=False)
    apparent_solar = db.Column(db.String(50), nullable=False)
    sidereal_result = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Initialize the actual database file inside the app context
with app.app_context():
    db.create_all()

# -------------------------------------------------------------------
# 🌌 APPLICATION PAGE ROUTES
# -------------------------------------------------------------------

@app.route('/')
def index():
    """Renders the Home dashboard panel containing the 3D rotating planet."""
    return render_template('index.html')


@app.route('/analysis')
def analysis():
    """Renders the interactive workspace page containing the global map engine."""
    return render_template('analysis.html')


@app.route('/execute_analysis', methods=['POST'])
def execute_analysis():
    """
    Handles coordinate input calculation processing.
    Extracts form inputs, runs mock transformations, saves logs to the 
    live database, and displays the high-fidelity results screen.
    """
    # 1. Capture spatial variables from user input form strings
    lat = float(request.form.get('latitude', 0.0))
    lon = float(request.form.get('longitude', 0.0))
    date_val = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))
    time_val = request.form.get('time', '12:00')
    timezone_val = request.form.get('timezone', '0')

    # 2. Mock calculations framework placeholder (Sprint 2 will drop mathematical equations here)
    mock_mean = "12:15:20"
    mock_apparent = "12:18:45"
    mock_sidereal = "14:53:12"
    
    # 3. Commit inputs and calculations directly into the active SQLite database log
    try:
        new_log = AnalysisLog(
            latitude=lat,
            longitude=lon,
            date_string=date_val,
            time_string=time_val,
            mean_solar=mock_mean,
            apparent_solar=mock_apparent,
            sidereal_result=mock_sidereal
        )
        db.session.add(new_log)
        db.session.commit()
    except Exception as e:
        print(f"Database Error: {e}")
        db.session.rollback()

    # 4. Packaging structural data context array for output visualization rendering
    data_packet = {
        'latitude': lat,
        'longitude': lon,
        'date': date_val,
        'time': time_val,
        'timezone': timezone_val,
        'mean_solar': mock_mean,
        'apparent_solar': mock_apparent,
        'sidereal': mock_sidereal,
        'sunrise': '06:42:15',
        'solar_noon': '12:18:45',
        'sunset': '18:55:30'
    }
    
    return render_template('results.html', data=data_packet)


@app.route('/learn')
def learn():
    """Renders the interactive educational textbook/documentation matrix."""
    return render_template('learn.html')


@app.route('/ai')
def ai():
    """Renders the custom educational AI chat terminal shell interface."""
    return render_template('ai.html')


@app.route('/about')
def about():
    """Renders the standard system project profile and final presentation brief."""
    return render_template('about.html')


# -------------------------------------------------------------------
# 🚀 APP SERVER CORE LAUNCH ENGINE
# -------------------------------------------------------------------
if __name__ == '__main__':
    # Set to debug mode for immediate code reload capabilities
    app.run(debug=True, port=5000)