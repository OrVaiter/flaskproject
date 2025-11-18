from flask  import Flask, request, jsonify, render_template

# flask - ספרייה ליצירת שרת אינטרנט פשוט בפייתון.
# request, jsonify, render_template – מאפשרים לקבל בקשות HTTP/להחזיר תגובות בפורמט JSON/ולהציג דפי HTML

from datetime import datetime, timedelta, timezone #ניהול תאריכים ושעות
import requests # שליחת בקשות HTTP (למשל, אל Discord)
import sqlite3 # עבודה עם מסד נתונים מקומי (SQLite)
import os # גישה למשתני סביבה, שימושית לאבטחה.

app = Flask(__name__) # יצירת מופע של אפליקציית Flask.

# 🧩 שלב 1 – הגדרות כלליות
# -------------------------------------------------------------------------

# קבלת ה-Webhook מהסביבה (עדיף על פני קשיח בקוד)
DISCORD_WEBHOOK_URL = os.getenv(
    "DISCORD_WEBHOOK_URL",
    "https://discord.com/api/webhooks/1437841607620821104/lbbXog-78SoycOuI-rbQIAZlzwecCDJbEdxyZyQhMKI7yD2BbBRazL6G-ys3gampu7yR"
)

# טוקן שמשמש לאימות בקשות (מניעת שליחה לא מורשית)
SECRET_TOKEN = "MySecureToken123"


# 🧱 שלב 2 – אתחול מסד הנתונים
# ----------------------------------------------------------------------------
def init_db():
    # נוצר מסד נתונים בשם messages.db אם אינו קיים.
    conn = sqlite3.connect('messages.db')
    cursor = conn.cursor()
    #נוצרה טבלה messages עם שלושה שדות:
    # id – מפתח ראשי (אוטומטי).
    # text – טקסט ההודעה.
    # timestamp – זמן הוספת ההודעה (ברירת מחדל: הזמן הנוכחי).
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit() # הפעולה הזו שומרת את כל השינויים שבוצעו במסד הנתונים (כמו יצירת הטבלה)
    conn.close() # סוגר את הקשר עם מסד הנתונים — פעולה חשובה כדי לשחרר משאבים

init_db() # קריאה לפונקציה - בכל פעם שהשרת מופעל - הוא יוודא שהמסד נתונים מוכן לעבודה/אם אין טבלה היא תיווצר

# 📨 שלב 3 – קבלת הודעה ושליחה ל-Discord
# -------------------------------------------------------------------------------
# זו נקודת קצה (endpoint) שמקבלת בקשות POST בכתובת /input_text
@app.route('/input_text', methods=['POST'])
def input_text():
    data = request.get_json(silent=True) or {}

    # אימות טוקן - מבטיח שרק מי שמחזיק בטוקן יכול לשלוח הודעות
    token = data.get('token')
    if token != SECRET_TOKEN:
        return jsonify({'error': 'Unauthorized'}), 401

    # ולידציה לטקסט
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({'error': 'Text cannot be empty'}), 400

    # בדיקה שאין מילות SQL חשודות (אבטחה בסיסית)
    forbidden_words = ["drop", "delete", "insert into"]
    if any(word in text.lower() for word in forbidden_words):
        return jsonify({'error': 'Forbidden content'}), 400

    try:
        # שמירה במסד הנתונים
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (text) VALUES (?)", (text,))
        conn.commit()
        conn.close()

        # שליחה ל-Discord
        payload = {'content': text}
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)

        if response.status_code == 204:
            print(f"[INFO] Message sent successfully: {text}")
            return jsonify({'message': 'Message sent to Discord successfully', 'text': text}), 200
        else:
            print(f"[ERROR] Discord response: {response.status_code} - {response.text}")
            return jsonify({'error': 'Failed to send message', 'details': response.text}), 500

    except Exception as e:
        print(f"[EXCEPTION] {e}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500


# 📋 שלב 4 – שליפה של הודעות אחרונות (30 דקות)
# ------------------------------------------------------------------------------------
@app.route('/get_messages', methods=['GET'])
def get_messages():
    time_threshold = datetime.now(timezone.utc) - timedelta(minutes=30)
    try:
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT text, timestamp FROM messages WHERE timestamp >= ?",
            (time_threshold.strftime("%Y-%m-%d %H:%M:%S"),)
        )
        rows = cursor.fetchall()
        conn.close()

        messages = [{'text': row[0], 'timestamp': row[1]} for row in rows]

        return jsonify({
            'count': len(messages),
            'recent_messages': messages
        })
    except Exception as e:
        print(f"[EXCEPTION] {e}")
        return jsonify({'error': 'Failed to retrieve messages', 'details': str(e)}), 500


# 🖥️ שלב 5 – תצוגת HTML של ההודעות האחרונות
# ------------------------------------------------------------------------------------
@app.route('/messages', methods=['GET'])
def messages_view():
    time_threshold = datetime.now(timezone.utc) - timedelta(minutes=30)

    try:
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT text, timestamp FROM messages WHERE timestamp >= ?",
            (time_threshold.strftime("%Y-%m-%d %H:%M:%S"),)
        )
        rows = cursor.fetchall()
        conn.close()

        messages = [{'text': row[0], 'timestamp': row[1]} for row in rows]
        return render_template("messages.html", messages=messages)
    except Exception as e:
        print(f"[EXCEPTION] {e}")
        return f"<h3>שגיאה בטעינת הדף: {e}</h3>", 500
#------------------------------------------------------------------
# 🧩 שלב חדש – דף סאבמיט
@app.route('/', methods=['GET'])
def submit_page():
    return render_template("submit.html")
#------------------------------------------------------------------
# יצירת בקשה לשרת לאיפוס הטבלה
@app.route('/reset_db', methods=['POST'])
def reset_db():
    try:
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages")
        conn.commit()
        conn.close()
        return jsonify({"message": "All records deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 🚀 שלב 6 – הפעלת השרת
# ----------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


# ----------------------------------------------------------------
#גכעכשגשכגעדגעגדעדגעדגעגע