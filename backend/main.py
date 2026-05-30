from flask import Flask
from flask_cors import CORS
import sys
from pathlib import Path
import os

sys.path.append(str(Path(__file__).parent.parent))

try:
    from backend.app.routes.api import api_bp
    from backend.config import Config
except ImportError:
    from app.routes.api import api_bp
    from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    Config.init_app(app)

    # CORS config
    CORS(app, resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    print(f"UPLOAD_FOLDER = {app.config['UPLOAD_FOLDER']}")

    #  SUPPRESSION DU PRÉFIXE '/api'
    app.register_blueprint(api_bp)

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        print(" Routes enregistrées :")
        for rule in app.url_map.iter_rules():
            print(rule)

    app.run(debug=app.config['DEBUG'], host='0.0.0.0', port=5000)
