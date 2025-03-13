from flask import Flask, request, jsonify, g, render_template
import sqlite3
import time

app = Flask(__name__)
DATABASE = 'coupons.db'
CLAIM_COOLDOWN = 60  # Users can claim once every 60 seconds

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

@app.route('/')
def index():
    return render_template('index.html')  # Serve the frontend

@app.route('/coupon', methods=['GET'])
def get_coupon():
    user_id = request.remote_addr  # Track by IP
    db = get_db()
    cursor = db.cursor()

    # Check if user exists
    cursor.execute("SELECT last_claim_time FROM users WHERE identifier = ?", (user_id,))
    user = cursor.fetchone()
    current_time = int(time.time())

    if user and current_time - user['last_claim_time'] < CLAIM_COOLDOWN:
        return jsonify({"error": "Wait before claiming another coupon."}), 429

    # Get next coupon
    cursor.execute("SELECT * FROM coupons ORDER BY assigned_count ASC LIMIT 1")
    coupon = cursor.fetchone()

    if not coupon:
        return jsonify({"error": "No coupons available."}), 404

    # Update coupon count
    cursor.execute("UPDATE coupons SET assigned_count = assigned_count + 1 WHERE id = ?", (coupon['id'],))

    # Update or insert user claim time
    if user:
        cursor.execute("UPDATE users SET last_claim_time = ? WHERE identifier = ?", (current_time, user_id))
    else:
        cursor.execute("INSERT INTO users (identifier, last_claim_time) VALUES (?, ?)", (user_id, current_time))

    db.commit()
    return jsonify({"coupon": coupon['code']})

if __name__ == '__main__':
    app.run(debug=True)

