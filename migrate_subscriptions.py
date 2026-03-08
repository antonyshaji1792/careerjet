
import sqlite3
import os

db_path = os.path.join('instance', 'careerjet.db')
if not os.path.exists(db_path):
    db_path = 'careerjet.db'

print(f"Connecting to database: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create plans table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(50) NOT NULL,
        slug VARCHAR(50) NOT NULL UNIQUE,
        stripe_price_id VARCHAR(100) UNIQUE,
        price FLOAT NOT NULL,
        currency VARCHAR(10) DEFAULT 'USD',
        interval VARCHAR(20) DEFAULT 'month',
        is_active BOOLEAN DEFAULT 1,
        features JSON,
        created_at DATETIME,
        updated_at DATETIME
    )
    ''')
    
    # Create subscriptions table (replacing old one if exists)
    # Check if subscriptions exists
    cursor.execute("PRAGMA table_info(subscriptions)")
    if cursor.fetchall():
        print("Table subscriptions already exists. Renaming for backup.")
        cursor.execute("ALTER TABLE subscriptions RENAME TO subscriptions_old")

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        plan_id INTEGER NOT NULL,
        status VARCHAR(50) DEFAULT 'active',
        stripe_subscription_id VARCHAR(100) UNIQUE,
        stripe_customer_id VARCHAR(100),
        current_period_start DATETIME,
        current_period_end DATETIME,
        cancel_at_period_end BOOLEAN DEFAULT 0,
        created_at DATETIME,
        updated_at DATETIME,
        FOREIGN KEY(user_id) REFERENCES user(id),
        FOREIGN KEY(plan_id) REFERENCES plans(id)
    )
    ''')
    
    # Create subscription_history table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS subscription_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        subscription_id INTEGER,
        event_type VARCHAR(100),
        old_status VARCHAR(50),
        new_status VARCHAR(50),
        old_plan_id INTEGER,
        new_plan_id INTEGER,
        metadata_json JSON,
        created_at DATETIME,
        FOREIGN KEY(user_id) REFERENCES user(id),
        FOREIGN KEY(subscription_id) REFERENCES subscriptions(id)
    )
    ''')
    
    # Seed default plans
    cursor.execute("SELECT id FROM plans WHERE slug='pro-monthly'")
    if not cursor.fetchone():
        print("Seeding default plans...")
        import json
        now = "2026-02-06 16:30:00"
        cursor.execute('''
        INSERT INTO plans (name, slug, price, interval, features, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('Pro Monthly', 'pro-monthly', 29.0, 'month', json.dumps(['AI Resume Builder', 'Unlimited Job Matches', 'Interview Coaching']), now, now))
        
        cursor.execute('''
        INSERT INTO plans (name, slug, price, interval, features, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('Enterprise', 'enterprise-monthly', 99.0, 'month', json.dumps(['All Pro Features', 'Dedicated Support', 'Team Collaboration']), now, now))

    conn.commit()
    conn.close()
    print("Database migration for subscriptions completed.")
        
except Exception as e:
    print(f"Error migrating database: {e}")
