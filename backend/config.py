import os

class Config:
    # Chemin vers le dossier où seront enregistrés les fichiers CSV uploadés
    
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'data')

    
    # Types de fichiers autorisés pour l'upload
    ALLOWED_EXTENSIONS = {'csv', 'pdf'}

    
    # Taille maximale d’un fichier uploadé (ici 10 Mo)
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024

    # Active le mode debug de Flask (affiche les erreurs dans le navigateur)
    DEBUG = True
