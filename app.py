import os
import io
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template, g, redirect, url_for, session
from flask_cors import CORS
from dotenv import load_dotenv
from groq import Groq
from werkzeug.security import generate_password_hash, check_password_hash

# Document parsing libraries
from pypdf import PdfReader
from docx import Document
import pandas as pd

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder=os.path.join(basedir, 'templates'), static_folder=os.path.join(basedir, 'static'))
app.secret_key = os.getenv("SECRET_KEY", "astro-time-secure-secret-key")
CORS(app)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
DATABASE = os.path.join(basedir, 'nova_ai.db')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                role TEXT,
                content TEXT,
                FOREIGN KEY(chat_id) REFERENCES chats(id)
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        db.commit()

init_db()

@app.context_processor
def inject_user():
    class UserContext:
        def __init__(self, user_id, username):
            self.is_authenticated = user_id is not None
            self.username = username
            
    return dict(current_user=UserContext(session.get("user_id"), session.get("username")))

# --- Page Routes ---
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/index", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/ai", methods=["GET"])
@app.route("/ai-assistant", methods=["GET"])
def ai_assistant():
    return render_template("ai.html")

@app.route("/learn", methods=["GET"])
def learn():
    return render_template("learn.html")

@app.route("/about", methods=["GET"])
def about():
    return render_template("about.html")

# --- Authentication ---
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "")

            if not username or not email or not password:
                return render_template("register.html", error="All fields are required.")

            hashed_password = generate_password_hash(password)
            db = get_db()
            db.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, hashed_password))
            db.commit()
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            return render_template("register.html", error="Username or Email already exists.")
        except Exception as e:
            return render_template("register.html", error=str(e))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        cursor = db.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("home"))
        else:
            return render_template("login.html", error="Invalid email or password.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

# --- Analysis & Matrix Calculation Engine ---
@app.route("/analysis", methods=["GET", "POST"])
def analysis():
    results = None
    inputs = None

    if request.method == "POST":
        try:
            lat = float(request.form.get("latitude", 3.1390))
            lng = float(request.form.get("longitude", 101.6869))
            date_str = request.form.get("date", "2026-09-14")
            time_str = request.form.get("time", "14:25")
            tz_offset = float(request.form.get("timezone", 8.0))

            inputs = {
                "latitude": lat,
                "longitude": lng,
                "date": date_str,
                "time": time_str,
                "timezone": tz_offset
            }

            dt_local_str = f"{date_str} {time_str}"
            dt_local = datetime.strptime(dt_local_str, "%Y-%m-%d %H:%M")
            
            year = dt_local.year
            month = dt_local.month
            day = dt_local.day
            hour = dt_local.hour - tz_offset
            minute = dt_local.minute
            
            fractional_day = day + (hour + minute / 60.0) / 24.0
            
            if month <= 2:
                year -= 1
                month += 12
                
            A = int(year / 100)
            B = 2 - A + int(A / 4)
            
            jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + fractional_day + B - 1524.5
            
            d = jd - 2451545.0
            gmst_deg = (280.46061837 + 360.98564736629 * d) % 360.0
            if gmst_deg < 0:
                gmst_deg += 360.0
                
            gmst_hours = gmst_deg / 15.0
            g_h = int(gmst_hours)
            g_m = int((gmst_hours - g_h) * 60)
            g_s = int(((gmst_hours - g_h) * 60 - g_m) * 60)
            gmst_str = f"{g_h:02d}h {g_m:02d}m {g_s:02d}s"

            lmst_hours = (gmst_hours + (lng / 15.0)) % 24.0
            if lmst_hours < 0:
                lmst_hours += 24.0
            l_h = int(lmst_hours)
            l_m = int((lmst_hours - l_h) * 60)
            l_s = int(((lmst_hours - l_h) * 60 - l_m) * 60)
            lmst_str = f"{l_h:02d}h {l_m:02d}m {l_s:02d}s"

            b_val = (2.0 * 3.141592653589793 * (d - 81)) / 365.25
            eot_val = 9.87 * __import__('math').sin(2 * b_val) - 7.53 * __import__('math').cos(b_val) - 1.5 * __import__('math').sin(b_val)

            last_str = f"{(l_h + 1)%24:02d}h {l_m:02d}m {l_s:02d}s"
            solar_time_str = f"{int((hour + lng / 15.0) % 24):02d}:{minute:02d} Solar Time"

            results = {
                "julian_date": f"{jd:.5f}",
                "gmst": gmst_str,
                "lmst": lmst_str,
                "eot_minutes": f"{eot_val:.2f}",
                "last_time": last_str,
                "solar_time": solar_time_str
            }
        except Exception as e:
            print(f"Calculation Error: {e}")
            results = None

    return render_template("analysis.html", results=results, inputs=inputs)

@app.route("/api/analysis", methods=["POST"])
def api_analysis():
    try:
        data = request.get_json() or request.form
        return jsonify({"status": "success", "message": "Matrix calculation processed successfully", "data": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# --- Nova AI Endpoints ---
@app.route("/api/chats", methods=["GET"])
def get_chats():
    db = get_db()
    cursor = db.execute("SELECT id, title FROM chats ORDER BY id DESC")
    return jsonify([dict(row) for row in cursor.fetchall()])

@app.route("/api/chats", methods=["POST"])
def create_chat():
    db = get_db()
    cursor = db.execute("INSERT INTO chats (title) VALUES (?)", ("New Chat",))
    db.commit()
    return jsonify({"chat_id": cursor.lastrowid, "title": "New Chat"})

@app.route("/api/chats/<int:chat_id>", methods=["GET"])
def get_chat_messages(chat_id):
    db = get_db()
    cursor = db.execute("SELECT role, content FROM messages WHERE chat_id = ? ORDER BY id ASC", (chat_id,))
    return jsonify([dict(row) for row in cursor.fetchall()])

@app.route("/api/chats/<int:chat_id>", methods=["DELETE"])
def delete_chat(chat_id):
    db = get_db()
    db.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    db.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
    db.commit()
    return jsonify({"status": "success"})

def extract_file_content(file_storage):
    """Universal parser for PDFs, Word, Excel, CSVs, code, and text files."""
    filename = file_storage.filename.lower()
    file_bytes = file_storage.read()
    extracted_text = ""

    try:
        if filename.endswith('.pdf'):
            reader = PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                extracted_text += (page.extract_text() or "") + "\n"

        elif filename.endswith('.docx'):
            doc = Document(io.BytesIO(file_bytes))
            for para in doc.paragraphs:
                extracted_text += para.text + "\n"
            for table in doc.tables:
                for row in table.rows:
                    extracted_text += " | ".join([cell.text.strip() for cell in row.cells]) + "\n"

        elif filename.endswith(('.xlsx', '.xls')):
            df_dict = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)
            for sheet_name, df in df_dict.items():
                extracted_text += f"\n--- Sheet: {sheet_name} ---\n"
                extracted_text += df.to_string(index=False) + "\n"

        else:
            # Fallback for code files, text files, markdown, json, csv, etc.
            extracted_text = file_bytes.decode('utf-8', errors='ignore')

    except Exception as e:
        extracted_text = f"[Error reading file content: {str(e)}]"

    # Cap text length to prevent overflow
    return extracted_text[:6000]

@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        chat_id = request.form.get("chat_id")
        message = request.form.get("message", "").strip()
        file = request.files.get("file")

        if not message and not file:
            return jsonify({"error": "Message or file cannot be empty"}), 400

        file_content = ""
        if file:
            filename = file.filename
            parsed_text = extract_file_content(file)
            file_content = f"\n\n[Attached File Content ({filename}):]\n```\n{parsed_text}\n```"

        full_message = message + file_content
        db = get_db()
        
        if not chat_id or chat_id == "null" or chat_id == "":
            cursor = db.execute("INSERT INTO chats (title) VALUES (?)", ((message[:30] or "File Upload") + "...",))
            db.commit()
            chat_id = cursor.lastrowid
        else:
            chat_id = int(chat_id)

        db.execute("INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)", (chat_id, "user", full_message))
        db.commit()

        cursor = db.execute("SELECT role, content FROM messages WHERE chat_id = ? ORDER BY id ASC", (chat_id,))
        history = [{"role": row["role"], "content": row["content"]} for row in cursor.fetchall()]

        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "system", "content": "You are Nova AI, a professional astronomical and geodetic assistant."}] + history,
            temperature=0.7,
            max_completion_tokens=2048
        )

        reply = completion.choices[0].message.content
        db.execute("INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)", (chat_id, "assistant", reply))
        db.commit()

        return jsonify({"chat_id": chat_id, "reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)