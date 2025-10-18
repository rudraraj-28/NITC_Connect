# app.py - main Flask backend
import sqlite3
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import bcrypt
import jwt
from functools import wraps
from datetime import datetime, timedelta
from pathlib import Path

# ===== CONFIG =====
JWT_SECRET = "REPLACE_THIS_WITH_A_RANDOM_SECRET"  # <- change for production and store in env var
JWT_ALGO = "HS256"
DB_FILE = "nitc.db"

# ===== APP =====
app = Flask(__name__, static_folder='../frontend', static_url_path='/')
CORS(app)

# ===== DB HELPERS =====
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# ===== AUTH HELPERS =====
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        header = request.headers.get('Authorization', None)
        if header:
            parts = header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]
        if not token:
            return jsonify({'error': 'Token is missing.'}), 401
        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
            request.user = data
        except Exception as e:
            return jsonify({'error': 'Token is invalid or expired.'}), 401
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if getattr(request, 'user', None) and request.user.get('role') == 'admin':
            return f(*args, **kwargs)
        return jsonify({'error': 'Admin access required.'}), 403
    return decorated

def is_nitc_email(email: str):
    return isinstance(email, str) and email.lower().endswith('@nitc.ac.in')

# ===== AUTH ROUTES =====
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    name = data.get('name','').strip()
    email = data.get('email','').strip().lower()
    password = data.get('password','')
    if not (name and email and password):
        return jsonify({'error':'name,email,password required'}), 400
    if not is_nitc_email(email):
        return jsonify({'error':'Register with your @nitc.ac.in email'}), 400
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)',
                  (name,email,hashed.decode('utf-8'),'student'))
        conn.commit()
        user_id = c.lastrowid
        token = jwt.encode({'id':user_id,'email':email,'role':'student',
                            'exp': datetime.utcnow()+timedelta(days=7)}, JWT_SECRET, algorithm=JWT_ALGO)
        return jsonify({'token': token})
    except sqlite3.IntegrityError:
        return jsonify({'error':'Email already registered'}), 400
    finally:
        conn.close()

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email','').strip().lower()
    password = data.get('password','')
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE email=?', (email,))
    row = c.fetchone()
    conn.close()
    if not row:
        return jsonify({'error':'Invalid credentials'}), 400
    stored = row['password']
    try:
        ok = bcrypt.checkpw(password.encode('utf-8'), stored.encode('utf-8'))
    except Exception:
        ok = False
    if not ok:
        return jsonify({'error':'Invalid credentials'}), 400
    token = jwt.encode({'id':row['id'],'email':row['email'],'role':row['role'],
                        'exp': datetime.utcnow()+timedelta(days=7)}, JWT_SECRET, algorithm=JWT_ALGO)
    return jsonify({'token':token, 'name': row['name'], 'role': row['role']})

# ===== SIMPLE PUBLIC ENDPOINTS =====
@app.route('/api/events', methods=['GET','POST'])
@token_required
def events():
    conn = get_db()
    c = conn.cursor()
    if request.method == 'GET':
        c.execute('SELECT * FROM events ORDER BY start_date ASC')
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return jsonify(rows)
    else:
        # create event (admin only)
        if request.user.get('role')!='admin':
            conn.close()
            return jsonify({'error':'Admin required'}), 403
        data = request.get_json() or {}
        c.execute('INSERT INTO events (title,description,start_date,end_date,venue) VALUES (?,?,?,?,?)',
                  (data.get('title'), data.get('description'), data.get('start_date'), data.get('end_date'), data.get('venue')))
        conn.commit()
        conn.close()
        return jsonify({'ok':True})

# ===== MARKETPLACE =====
@app.route('/api/marketplace', methods=['GET','POST','DELETE','PUT'])
@token_required
def marketplace():
    conn = get_db()
    c = conn.cursor()
    if request.method == 'GET':
        c.execute('SELECT m.*, u.name as owner FROM marketplace m LEFT JOIN users u ON m.user_id=u.id ORDER BY m.created_at DESC')
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return jsonify(rows)
    if request.method == 'POST':
        data = request.get_json() or {}
        c.execute('INSERT INTO marketplace (user_id,title,description,price,image) VALUES (?,?,?,?,?)',
                  (request.user['id'], data.get('title'), data.get('description'), data.get('price',''), data.get('image','')))
        conn.commit()
        conn.close()
        return jsonify({'ok':True})
    if request.method == 'PUT':
        data = request.get_json() or {}
        item_id = data.get('id')
        # only owner or admin can edit
        c.execute('SELECT user_id FROM marketplace WHERE id=?', (item_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return jsonify({'error':'Not found'}), 404
        if request.user.get('role')!='admin' and row['user_id'] != request.user['id']:
            conn.close()
            return jsonify({'error':'Forbidden'}), 403
        c.execute('UPDATE marketplace SET title=?,description=?,price=?,image=? WHERE id=?',
                  (data.get('title'), data.get('description'), data.get('price'), data.get('image'), item_id))
        conn.commit()
        conn.close()
        return jsonify({'ok':True})
    if request.method == 'DELETE':
        data = request.get_json() or {}
        item_id = data.get('id')
        c.execute('SELECT user_id FROM marketplace WHERE id=?', (item_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return jsonify({'error':'Not found'}), 404
        if request.user.get('role')!='admin' and row['user_id'] != request.user['id']:
            conn.close()
            return jsonify({'error':'Forbidden'}), 403
        c.execute('DELETE FROM marketplace WHERE id=?', (item_id,))
        conn.commit()
        conn.close()
        return jsonify({'ok':True})

# ===== LOST & FOUND =====
@app.route('/api/lostfound', methods=['GET','POST','PUT','DELETE'])
@token_required
def lostfound():
    conn = get_db(); c = conn.cursor()
    if request.method == 'GET':
        c.execute('SELECT lf.*, u.name as owner FROM lostfound lf LEFT JOIN users u ON lf.user_id=u.id ORDER BY lf.created_at DESC')
        rows = [dict(r) for r in c.fetchall()]; conn.close(); return jsonify(rows)
    if request.method == 'POST':
        data = request.get_json() or {}
        c.execute('INSERT INTO lostfound (user_id,title,description,status,image) VALUES (?,?,?,?,?)',
                  (request.user['id'], data.get('title'), data.get('description'), data.get('status','lost'), data.get('image','')))
        conn.commit(); conn.close(); return jsonify({'ok':True})
    if request.method == 'PUT':
        data = request.get_json() or {}
        item_id = data.get('id')
        c.execute('SELECT user_id FROM lostfound WHERE id=?', (item_id,))
        row = c.fetchone()
        if not row:
            conn.close(); return jsonify({'error':'Not found'}), 404
        if request.user.get('role')!='admin' and row['user_id'] != request.user['id']:
            conn.close(); return jsonify({'error':'Forbidden'}), 403
        c.execute('UPDATE lostfound SET title=?,description=?,status=?,image=? WHERE id=?',
                  (data.get('title'), data.get('description'), data.get('status','lost'), data.get('image',''), item_id))
        conn.commit(); conn.close(); return jsonify({'ok':True})
    if request.method == 'DELETE':
        data = request.get_json() or {}; item_id = data.get('id')
        c.execute('SELECT user_id FROM lostfound WHERE id=?', (item_id,))
        row = c.fetchone()
        if not row:
            conn.close(); return jsonify({'error':'Not found'}), 404
        if request.user.get('role')!='admin' and row['user_id'] != request.user['id']:
            conn.close(); return jsonify({'error':'Forbidden'}), 403
        c.execute('DELETE FROM lostfound WHERE id=?', (item_id,)); conn.commit(); conn.close(); return jsonify({'ok':True})

# ===== TICKETS (Hostel) =====
@app.route('/api/tickets', methods=['GET','POST','PUT'])
@token_required
def tickets():
    conn = get_db(); c = conn.cursor()
    if request.method == 'GET':
        # admin can view all, students only their tickets
        if request.user.get('role') == 'admin':
            c.execute('SELECT t.*, u.name as owner FROM tickets t LEFT JOIN users u ON t.user_id=u.id ORDER BY t.created_at DESC')
        else:
            c.execute('SELECT t.*, u.name as owner FROM tickets t LEFT JOIN users u ON t.user_id=u.id WHERE t.user_id=? ORDER BY t.created_at DESC', (request.user['id'],))
        rows = [dict(r) for r in c.fetchall()]; conn.close(); return jsonify(rows)
    if request.method == 'POST':
        data = request.get_json() or {}
        c.execute('INSERT INTO tickets (user_id,hostel,issue,status) VALUES (?,?,?,?)',
                  (request.user['id'], data.get('hostel'), data.get('issue'), 'open'))
        conn.commit(); conn.close(); return jsonify({'ok':True})
    if request.method == 'PUT':
        data = request.get_json() or {}
        ticket_id = data.get('id')
        c.execute('SELECT user_id FROM tickets WHERE id=?', (ticket_id,))
        row = c.fetchone()
        if not row:
            conn.close(); return jsonify({'error':'Not found'}), 404
        # admin can change status, user can only add info (not implemented here)
        if request.user.get('role') != 'admin':
            conn.close(); return jsonify({'error':'Admin required to update ticket'}), 403
        c.execute('UPDATE tickets SET status=? WHERE id=?', (data.get('status','closed'), ticket_id))
        conn.commit(); conn.close(); return jsonify({'ok':True})

# ===== BOOKINGS (Hall) =====
@app.route('/api/bookings', methods=['GET','POST','PUT'])
@token_required
def bookings():
    conn = get_db(); c = conn.cursor()
    if request.method == 'GET':
        # admin sees all
        if request.user.get('role') == 'admin':
            c.execute('SELECT b.*, u.name as owner FROM bookings b LEFT JOIN users u ON b.user_id=u.id ORDER BY b.date DESC')
        else:
            c.execute('SELECT b.*, u.name as owner FROM bookings b LEFT JOIN users u ON b.user_id=u.id WHERE b.user_id=? ORDER BY b.date DESC', (request.user['id'],))
        rows = [dict(r) for r in c.fetchall()]; conn.close(); return jsonify(rows)
    if request.method == 'POST':
        data = request.get_json() or {}
        c.execute('INSERT INTO bookings (user_id,hall_name,date,slot,status) VALUES (?,?,?,?,?)',
                  (request.user['id'], data.get('hall_name'), data.get('date'), data.get('slot'), 'pending'))
        conn.commit(); conn.close(); return jsonify({'ok':True})
    if request.method == 'PUT':
        data = request.get_json() or {}
        if request.user.get('role') != 'admin':
            return jsonify({'error':'Admin only'}), 403
        c.execute('UPDATE bookings SET status=? WHERE id=?', (data.get('status'), data.get('id')))
        conn.commit(); conn.close(); return jsonify({'ok':True})

# ===== CLUBS & PLACEMENTS (Admin manage) =====
@app.route('/api/clubs', methods=['GET','POST','PUT','DELETE'])
@token_required
def clubs():
    conn = get_db(); c = conn.cursor()
    if request.method == 'GET':
        c.execute('SELECT * FROM clubs ORDER BY name')
        rows = [dict(r) for r in c.fetchall()]; conn.close(); return jsonify(rows)
    if request.method == 'POST':
        if request.user.get('role') != 'admin':
            conn.close(); return jsonify({'error':'Admin required'}), 403
        data = request.get_json() or {}
        c.execute('INSERT INTO clubs (name,description,contact) VALUES (?,?,?)', (data.get('name'), data.get('description'), data.get('contact')))
        conn.commit(); conn.close(); return jsonify({'ok':True})
    if request.method == 'PUT':
        if request.user.get('role') != 'admin':
            conn.close(); return jsonify({'error':'Admin required'}), 403
        data = request.get_json() or {}
        c.execute('UPDATE clubs SET name=?,description=?,contact=? WHERE id=?', (data.get('name'), data.get('description'), data.get('contact'), data.get('id')))
        conn.commit(); conn.close(); return jsonify({'ok':True})
    if request.method == 'DELETE':
        if request.user.get('role') != 'admin':
            conn.close(); return jsonify({'error':'Admin required'}), 403
        data = request.get_json() or {}
        c.execute('DELETE FROM clubs WHERE id=?', (data.get('id'),))
        conn.commit(); conn.close(); return jsonify({'ok':True})

@app.route('/api/placements', methods=['GET','POST'])
@token_required
def placements():
    conn = get_db(); c = conn.cursor()
    if request.method == 'GET':
        c.execute('SELECT * FROM placements ORDER BY year DESC')
        rows = [dict(r) for r in c.fetchall()]; conn.close(); return jsonify(rows)
    else:
        if request.user.get('role') != 'admin':
            conn.close(); return jsonify({'error':'Admin required'}), 403
        data = request.get_json() or {}
        c.execute('INSERT INTO placements (year,total_students,placed,avg_ctc) VALUES (?,?,?,?)',
                  (data.get('year'), data.get('total_students'), data.get('placed'), data.get('avg_ctc')))
        conn.commit(); conn.close(); return jsonify({'ok':True})

# ===== SCRAPER STUB (brownie points) =====
@app.route('/api/scrape_placements', methods=['POST'])
@token_required
@admin_required
def scrape_placements():
    # This is a stub to demonstrate scraping: run carefully and respect robots.txt
    import requests
    from bs4 import BeautifulSoup
    url = request.json.get('url')
    if not url:
        return jsonify({'error':'Provide url in {"url": "..."}'}), 400
    try:
        r = requests.get(url, timeout=8)
        soup = BeautifulSoup(r.text, 'html.parser')
        # This is generic — you'll need to adapt selectors for actual NITC page
        # Example: find avg CTC numeric in text
        text = soup.get_text(separator=' ')
        import re
        match = re.search(r'(\d+(?:\.\d+)?)\\s*(?:LPA|lpa|lakhs|lakhs per annum|cr)', text)
        avg = float(match.group(1)) if match else 0.0
        # store as current year
        c = get_db().cursor()
        c.execute('INSERT INTO placements (year,total_students,placed,avg_ctc) VALUES (?,?,?,?)',
                  (datetime.now().year, 0, 0, avg))
        c.connection.commit()
        c.connection.close()
        return jsonify({'ok':True, 'avg_ctc': avg})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== STATIC FILES (frontend) =====
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    frontend_folder = Path(app.static_folder)  # convert string to Path
    file_path = frontend_folder / path

    if path != "" and file_path.exists():
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

# ===== MAIN =====
if __name__ == '__main__':
    print("Starting NITCConnect backend on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
