from app import create_app, db
from app.models import User

app = create_app()

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=port)
