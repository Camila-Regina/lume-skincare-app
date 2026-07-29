"""
database.py
Handles all the SQLite work for Lumé: creating the tables and
reading and writing users and profiles.

Keeping the database code in its own file (separate from app.py) follows
the three tier idea from the design: the logic and the data are kept apart.
"""

import sqlite3

DB_NAME = "lume.db"


def get_connection():
    """Open a connection to the SQLite database file.

    row_factory lets us read columns by name (like row["email"])
    instead of by number, which makes the code easier to read.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the tables if they do not already exist.

    Called once when the app starts. Safe to run every time because
    of 'IF NOT EXISTS'.
    """
    conn = get_connection()
    cur = conn.cursor()

    # Users table: one row per registered person.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    # Profiles table: one skin profile per user.
    # user_id links each profile back to a row in the users table.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            skin_type TEXT,
            age TEXT,
            concerns TEXT,
            sensitivities TEXT,
            allergies TEXT,
            climate TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    conn.commit()
    conn.close()


# ---- User operations (part of CRUD: create and read) ----

def create_user(email, password_hash):
    """Insert a new user and return their new id."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        (email, password_hash),
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id


def get_user_by_email(email):
    """Find a user by their email. Returns the row, or None if not found."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cur.fetchone()
    conn.close()
    return user


# ---- Profile operations (create, read, update) ----

def get_profile(user_id):
    """Return the profile for a user, or None if they have not made one yet."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,))
    profile = cur.fetchone()
    conn.close()
    return profile


def save_profile(user_id, data):
    """Create or update a user's profile.

    If a profile already exists we update it, otherwise we insert a new one.
    This keeps the rule of one profile per user from the design.
    """
    conn = get_connection()
    cur = conn.cursor()

    existing = get_profile(user_id)
    if existing:
        cur.execute("""
            UPDATE profiles
            SET skin_type = ?, age = ?, concerns = ?, sensitivities = ?, allergies = ?, climate = ?
            WHERE user_id = ?
        """, (data["skin_type"], data["age"], data["concerns"],
              data["sensitivities"], data["allergies"], data["climate"], user_id))
    else:
        cur.execute("""
            INSERT INTO profiles (user_id, skin_type, age, concerns, sensitivities, allergies, climate)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, data["skin_type"], data["age"], data["concerns"],
              data["sensitivities"], data["allergies"], data["climate"]))

    conn.commit()
    conn.close()
