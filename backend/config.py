import os
from pathlib import Path

class Config:
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / 'data'
    MODELS_DIR = BASE_DIR / 'app' / 'models'

    UPLOAD_FOLDER = str(DATA_DIR)
    ALLOWED_EXTENSIONS = {'csv', 'pdf'}
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024

    PLUGINS = {
        'finance': {
            'model_path': MODELS_DIR / 'finance' / 'regression_model.pkl',
            'preprocessing': 'standard'
        }
    }

    DEBUG = True
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-key-123')

    @classmethod
    def init_app(cls, app):
        cls.DATA_DIR.mkdir(exist_ok=True)
        (cls.MODELS_DIR / 'finance').mkdir(parents=True, exist_ok=True)
        app.config.from_object(cls)
