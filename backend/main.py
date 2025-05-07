from flask import Flask                   # Import de Flask
from flask_cors import CORS               # Pour activer les requêtes Cross-Origin (utile avec un front-end séparé)
from app.routes.api import api_bp         # On importe le blueprint qu’on a défini dans routes/api.py
from config import Config                 # On importe notre classe de configuration

def create_app():
    app = Flask(__name__)                 # Création de l'application Flask
    app.config.from_object(Config)        # Application des configurations depuis config.py
    CORS(app)                             # Activation de CORS (permet les requêtes du front-end vers cette API)

    app.register_blueprint(api_bp)        # Enregistrement de notre groupe de routes dans l'app

    return app

# Ce bloc permet d’exécuter le serveur uniquement si on lance ce fichier directement
if __name__ == '__main__':
    app = create_app()                    # Création de l'app via la fonction create_app
    app.run(debug=app.config['DEBUG'])    # Lancement du serveur avec le debug activé


