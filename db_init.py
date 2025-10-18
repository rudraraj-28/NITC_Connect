# db_init.py
# Run once to create the SQLite DB and tables

import sqlite3

def init():
    conn = sqlite3.connect('nitc.db')
    c = conn.cursor()
    c.execute('''
      CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT DEFAULT 'student',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    ''')
    c.execute('''
      CREATE TABLE IF NOT EXISTS marketplace (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        description TEXT,
        price TEXT,
        image TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    ''')
    c.execute('''
      CREATE TABLE IF NOT EXISTS lostfound (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        description TEXT,
        status TEXT DEFAULT 'lost',
        image TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    ''')
    c.execute('''
      CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        description TEXT,
        start_date TEXT,
        end_date TEXT,
        venue TEXT
      )
    ''')
    c.execute('''
      CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        hostel TEXT,
        issue TEXT,
        status TEXT DEFAULT 'open',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    ''')
    c.execute('''
      CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        hall_name TEXT,
        date TEXT,
        slot TEXT,
        status TEXT DEFAULT 'pending'
      )
    ''')
    c.execute('''
      CREATE TABLE IF NOT EXISTS clubs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        description TEXT,
        contact TEXT
      )
    ''')
    c.execute('''
      CREATE TABLE IF NOT EXISTS placements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year INTEGER,
        total_students INTEGER,
        placed INTEGER,
        avg_ctc REAL
      )
    ''')
    conn.commit()
    conn.close()
    print("Initialized nitc.db")

if __name__ == '__main__':
    init()
