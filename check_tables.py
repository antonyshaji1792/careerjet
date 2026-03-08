
import sqlite3
import os

db_path = os.path.join('instance', 'careerjet.db')
if not os.path.exists(db_path):
    db_path = 'careerjet.db'

print(f"Connecting to database: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    tables = ['ai_video_interviews', 'ai_video_questions', 'ai_video_answers', 'ai_video_evaluations', 'ai_video_summaries']
    
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        if not columns:
            print(f"Table {table} MISSING!")
        else:
            print(f"Table {table} exists with columns: {', '.join(columns)}")

    conn.close()
        
except Exception as e:
    print(f"Error checking database: {e}")
