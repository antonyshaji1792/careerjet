
import sqlite3
import os
import json
from datetime import datetime

db_path = os.path.join('instance', 'careerjet.db')
if not os.path.exists(db_path):
    db_path = 'careerjet.db'

print(f"Connecting to database: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if columns exist
    cursor.execute("PRAGMA table_info(plans)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'credits_per_interval' not in columns:
        print("Adding credits_per_interval to plans...")
        cursor.execute("ALTER TABLE plans ADD COLUMN credits_per_interval INTEGER DEFAULT 0")
    
    if 'rollover_allowed' not in columns:
        print("Adding rollover_allowed to plans...")
        cursor.execute("ALTER TABLE plans ADD COLUMN rollover_allowed BOOLEAN DEFAULT 0")

    # Update/Seed Plans with credits
    now = datetime.utcnow().isoformat()
    
    # 1. Pro Plan
    cursor.execute("SELECT id FROM plans WHERE slug='pro-monthly'")
    if cursor.fetchone():
        print("Updating Pro plan...")
        cursor.execute('''
            UPDATE plans SET 
                credits_per_interval = 500,
                rollover_allowed = 1,
                features = ?
            WHERE slug='pro-monthly'
        ''', (json.dumps(['500 AI Credits', 'AI Resume Builder', 'Unlimited Job Matches', 'Pro Interview Coaching', 'Rollover Credits']),))
    else:
        print("Seeding Pro plan...")
        cursor.execute('''
            INSERT INTO plans (name, slug, price, interval, credits_per_interval, rollover_allowed, features, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('Pro Co-Pilot', 'pro-monthly', 29.0, 'month', 500, 1, json.dumps(['500 AI Credits', 'AI Resume Builder', 'Unlimited Job Matches', 'Pro Interview Coaching', 'Rollover Credits']), now, now))

    # 2. Enterprise Plan
    cursor.execute("SELECT id FROM plans WHERE slug='enterprise-monthly'")
    if cursor.fetchone():
        print("Updating Enterprise plan...")
        cursor.execute('''
            UPDATE plans SET 
                credits_per_interval = 2000,
                rollover_allowed = 1,
                features = ?
            WHERE slug='enterprise-monthly'
        ''', (json.dumps(['2000 AI Credits', 'All Pro Features', 'Dedicated Support', 'Priority AI Access', 'Rollover Credits']),))
    else:
        print("Seeding Enterprise plan...")
        cursor.execute('''
            INSERT INTO plans (name, slug, price, interval, credits_per_interval, rollover_allowed, features, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('Enterprise Elite', 'enterprise-monthly', 99.0, 'month', 2000, 1, json.dumps(['2000 AI Credits', 'All Pro Features', 'Dedicated Support', 'Priority AI Access', 'Rollover Credits']), now, now))

    # 3. Basic Plan (Free)
    cursor.execute("SELECT id FROM plans WHERE slug='basic-free'")
    if not cursor.fetchone():
        print("Seeding Basic plan...")
        cursor.execute('''
            INSERT INTO plans (name, slug, price, interval, credits_per_interval, rollover_allowed, features, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('Starter', 'basic-free', 0.0, 'month', 20, 0, json.dumps(['20 AI Credits', 'Basic Resume Builder', 'Job Discovery', 'Standard Templates']), now, now))

    conn.commit()
    conn.close()
    print("Plan data updated successfully.")
        
except Exception as e:
    print(f"Error updating plans: {e}")
