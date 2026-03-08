from app import create_app, db
from sqlalchemy import inspect

app = create_app()

with app.app_context():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    print("Tables in DB:")
    for t in tables:
        print(f"- {t}")
    
    if 'ai_interviews' in tables:
        print("ai_interviews exists in DB.")
    else:
        print("ai_interviews DOES NOT exist in DB.")
        
    if 'ai_video_interviews' in tables:
        print("ai_video_interviews exists in DB.")
    else:
        print("ai_video_interviews DOES NOT exist in DB.")
