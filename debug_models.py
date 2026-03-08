from app import create_app, db
import app.models

app = create_app()

with app.app_context():
    if 'ai_video_interviews' in db.metadata.tables:
        print("SUCCESS: ai_video_interviews IS registered.")
    else:
        print("FAILURE: ai_video_interviews is NOT registered.")
