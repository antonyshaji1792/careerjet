
import sqlite3
import os

db_path = os.path.join('instance', 'careerjet.db')
if not os.path.exists(db_path):
    # Try alternate path if not in instance/
    db_path = 'careerjet.db'

print(f"Connecting to database: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check current columns in application table
    cursor.execute("PRAGMA table_info(application)")
    columns = [row[1] for row in cursor.fetchall()]
    
    new_columns = [
        ('status_message', 'VARCHAR(255)'),
        ('error_message', 'TEXT'),
        ('screenshot_path', 'VARCHAR(255)')
    ]
    
    added = []
    for col_name, col_type in new_columns:
        if col_name not in columns:
            print(f"Adding column {col_name}...")
            cursor.execute(f"ALTER TABLE application ADD COLUMN {col_name} {col_type}")
            added.append(col_name)
    
    # Add columns to AnswerCache if needed
    cursor.execute("PRAGMA table_info(answer_cache)")
    answercache_columns = [row[1] for row in cursor.fetchall()]
    if answercache_columns and 'last_used_at' not in answercache_columns:
        print("Adding column last_used_at to answer_cache...")
        cursor.execute("ALTER TABLE answer_cache ADD COLUMN last_used_at DATETIME")
        added.append('answer_cache.last_used_at')

    conn.commit()
    conn.close()
    
    if added:
        print(f"Successfully added columns: {', '.join(added)}")
    else:
        print("No columns needed to be added.")
        
except Exception as e:
    print(f"Error updating database: {e}")
