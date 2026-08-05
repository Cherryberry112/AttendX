from app import app
from models import User
with app.app_context():
    admins = User.query.filter_by(type="admin").all()
    for a in admins:
        print(f"Admin: {a.username}, Email: {a.email}")
