
import sqlite3
import os

db_path = os.path.join('instance', 'careerjet.db')
if not os.path.exists(db_path):
    db_path = 'careerjet.db'

print(f"Connecting to database: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check current columns in ai_video_interviews table
    cursor.execute("PRAGMA table_info(ai_video_interviews)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if not columns:
        print("Table ai_video_interviews not found. Re-creating all tables might be needed.")
    else:
        new_columns = [
            ('video_url', 'VARCHAR(500)')
        ]
        
        added = []
        for col_name, col_type in new_columns:
            if col_name not in columns:
                print(f"Adding column {col_name} to ai_video_interviews...")
                cursor.execute(f"ALTER TABLE ai_video_interviews ADD COLUMN {col_name} {col_type}")
                added.append(col_name)
        
        conn.commit()
        if added:
            print(f"Successfully added columns: {', '.join(added)}")
        else:
            print("No columns needed to be added to ai_video_interviews.")

    conn.close()
        
except Exception as e:
    print(f"Error updating database: {e}")
