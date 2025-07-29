import os
from models import db
from flask import Flask
from route import routes
from sqlalchemy import text
from flask_cors import CORS
from dotenv import load_dotenv
from flask_migrate import Migrate

load_dotenv()

app = Flask(__name__)

class Config:
    SCHEDULER_API_ENABLED = True

app.config.from_object(Config)

CORS(
    app,
    supports_credentials=True,
    resources={r"/*": {"origins": [
        "http://localhost:5173",
        "https://hrms-admin-dashboard-xi.vercel.app",
    ]}},
    expose_headers=["Content-Type", "Authorization"],
    allow_headers=["Content-Type", "Authorization"]
)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

with app.app_context():
    try:
        db.session.execute(text('SELECT 1'))
        print("✅ Database connected successfully.")
        
        db.create_all()
        print("📦 Tables created successfully (if they didn't exist).")

    except Exception as e:
        print("❌ Failed to connect to the database:", e)

app.register_blueprint(routes)

if __name__ == "__main__":
    app.run(debug=True)
