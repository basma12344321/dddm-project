# backend/main.py

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
import sys
import os
from pathlib import Path

# ✅ Ajouter le dossier backend au path EN PREMIER
backend_dir = str(Path(__file__).parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Charger le .env
load_dotenv(os.path.join(Path(__file__).parent.parent, '.env'))

# ✅ Import direct sans try/except pour éviter le double import
from app.routes.api import api_bp
from app.routes.auth import auth_bp
from app.extensions import db
from app.models import User, Analysis, Simulation
from config import Config


def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)
    Config.init_app(app)

    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:dddm1234@localhost:5432/dddm_db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv(
        'JWT_SECRET_KEY',
        'super-secret-key-dddm-2025'
    )

    db.init_app(app)
    JWTManager(app)

    CORS(app, resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    print(f"UPLOAD_FOLDER = {app.config['UPLOAD_FOLDER']}")

    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')

    with app.app_context():
        db.create_all()
        print("Tables PostgreSQL créées avec succès !")

    return app


if __name__ == '__main__':
    app = create_app()

    with app.app_context():
        print("Routes enregistrées :")
        for rule in app.url_map.iter_rules():
            print(rule)

    app.run(debug=app.config['DEBUG'], host='0.0.0.0', port=5000, use_reloader=False)