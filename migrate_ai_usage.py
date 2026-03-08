
import sqlite3
import os

db_path = os.path.join('instance', 'careerjet.db')
if not os.path.exists(db_path):
    db_path = 'careerjet.db'

print(f"Connecting to database: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if ai_usage exists and drop it if it's the old one (optional, but requested new table)
    cursor.execute("DROP TABLE IF EXISTS ai_usage")

    # Create ai_usage_logs table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ai_usage_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        feature_type VARCHAR(50) NOT NULL,
        ai_model VARCHAR(100),
        credits_used INTEGER DEFAULT 0,
        tokens_used INTEGER DEFAULT 0,
        execution_time FLOAT,
        status VARCHAR(20),
        error_message TEXT,
        created_at DATETIME,
        FOREIGN KEY(user_id) REFERENCES user(id)
    )
    ''')
    
    conn.commit()
    conn.close()
    print("Database migration for AI usage logs completed.")
        
except Exception as e:
    print(f"Error migrating database: {e}")
