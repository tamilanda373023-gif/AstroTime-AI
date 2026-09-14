import os
import sqlite3
from flask import Flask, request, jsonify, render_template, g
from flask_cors import CORS
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder=os.path.join(basedir, 'templates'), static_folder=os.path.join(basedir, 'static'))
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
        db.commit()

init_db()

@app.context_processor
def inject_user():
    class AnonymousUser:
        is_authenticated = False
        is_anonymous = True
    return dict(current_user=AnonymousUser())

# --- Page Routes ---
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/ai", methods=["GET"])
@app.route("/ai-assistant", methods=["GET"])
def ai_page():
    return render_template("ai.html")

@app.route("/analysis", methods=["GET"])
def analysis():
    return render_template("analysis.html")

@app.route("/learn", methods=["GET"])
def learn():
    return render_template("learn.html")

@app.route("/about", methods=["GET"])
def about():
    return render_template("about.html")

# --- Nova AI API Endpoints ---
@app.route("/api/chats", methods=["GET"])
def get_chats():
    db = get_db()
    cursor = db.execute("SELECT id, title FROM chats ORDER BY id DESC")
    chats = [dict(row) for row in cursor.fetchall()]
    return jsonify(chats)

@app.route("/api/chats", methods=["POST"])
def create_chat():
    db = get_db()
    cursor = db.execute("INSERT INTO chats (title) VALUES (?)", ("New Chat",))
    db.commit()
    chat_id = cursor.lastrowid
    return jsonify({"chat_id": chat_id, "title": "New Chat"})

@app.route("/api/chats/<int:chat_id>", methods=["GET"])
def get_chat_messages(chat_id):
    db = get_db()
    cursor = db.execute("SELECT role, content FROM messages WHERE chat_id = ? ORDER BY id ASC", (chat_id,))
    messages = [dict(row) for row in cursor.fetchall()]
    return jsonify(messages)

@app.route("/api/chats/<int:chat_id>", methods=["DELETE"])
def delete_chat(chat_id):
    db = get_db()
    db.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    db.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
    db.commit()
    return jsonify({"status": "success"})

@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        chat_id = request.form.get("chat_id")
        message = request.form.get("message", "").strip()
        file = request.files.get("file")

        if not message and not file:
            return jsonify({"error": "Message or file cannot be empty"}), 400

        file_content_description = ""
        if file:
            filename = file.filename
            if filename.endswith(('.txt', '.csv', '.py', '.json', '.md', '.log')):
                file_text = file.read().decode('utf-8', errors='ignore')
                file_content_description = f"\n\n[Attached File: {filename}]\n```\n{file_text[:4000]}\n```"
            else:
                file_content_description = f"\n\n[Attached File: {filename} uploaded successfully]"

        full_message = message + file_content_description

        db = get_db()
        
        if not chat_id or chat_id == "null" or chat_id == "":
            cursor = db.execute("INSERT INTO chats (title) VALUES (?)", ((message[:30] or "File Upload") + "...",))
            db.commit()
            chat_id = cursor.lastrowid
        else:
            chat_id = int(chat_id)
            cursor = db.execute("SELECT title FROM chats WHERE id = ?", (chat_id,))
            row = cursor.fetchone()
            if row and row['title'] == 'New Chat':
                db.execute("UPDATE chats SET title = ? WHERE id = ?", ((message[:30] or "File Upload") + "...", chat_id))
                db.commit()

        db.execute("INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)", (chat_id, "user", full_message))
        db.commit()

        cursor = db.execute("SELECT role, content FROM messages WHERE chat_id = ? ORDER BY id ASC", (chat_id,))
        history = [{"role": row["role"], "content": row["content"]} for row in cursor.fetchall()]

        system_prompt = {
            "role": "system",
            "content": "You are Nova AI, a professional, highly capable astronomical and geodetic assistant built for Astro Time AI. Use markdown, tables, and LaTeX equations where appropriate."
        }
        
        messages_payload = [system_prompt] + history

        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=messages_payload,
            stream=False,
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