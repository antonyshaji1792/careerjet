
import sqlite3
import os

db_path = os.path.join('instance', 'careerjet.db')
if not os.path.exists(db_path):
    db_path = 'careerjet.db'

print(f"Connecting to database: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Update plans table
    cursor.execute("PRAGMA table_info(plans)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'credits_per_interval' not in columns:
        print("Updating plans table...")
        cursor.execute("ALTER TABLE plans ADD COLUMN credits_per_interval INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE plans ADD COLUMN rollover_allowed BOOLEAN DEFAULT 0")

    # Create user_credits table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_credits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        balance INTEGER DEFAULT 0,
        last_reset_at DATETIME,
        updated_at DATETIME,
        FOREIGN KEY(user_id) REFERENCES user(id)
    )
    ''')
    
    # Create credit_transactions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS credit_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        transaction_type VARCHAR(50) NOT NULL,
        feature_name VARCHAR(100),
        metadata_json JSON,
        created_at DATETIME,
        FOREIGN KEY(user_id) REFERENCES user(id)
    )
    ''')
    
    # Update seed plans with credits
    cursor.execute("UPDATE plans SET credits_per_interval = 100 WHERE slug = 'pro-monthly'")
    cursor.execute("UPDATE plans SET credits_per_interval = 500, rollover_allowed = 1 WHERE slug = 'enterprise-monthly'")

    conn.commit()
    conn.close()
    print("Database migration for credits completed.")
        
except Exception as e:
    print(f"Error migrating database: {e}")
