from flask import Blueprint, request, jsonify, current_app
import os
import pandas as pd
import pdfplumber  # Pour lire les fichiers PDF
#from app.core_engine.core_engine import predict_dummy#pour tester uniqument
from app.core_engine.core_engine import clean_data, predict, classify 


# Création d’un "blueprint", qui est une manière de modulariser les routes
api_bp = Blueprint('api', __name__)

# Fonction qui vérifie si un fichier a une extension autorisée
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

# Route POST /upload pour envoyer un fichier CSV ou PDF
@api_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400  # Erreur si aucun fichier envoyé
    
    file = request.files['file']                         # On récupère le fichier depuis la requête
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400  # Erreur si aucun fichier sélectionné
    
    if file and allowed_file(file.filename):
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)                              # Enregistrement du fichier sur le serveur
        return jsonify({"message": f"Fichier {file.filename} bien reçu."}), 200
    else:
        return jsonify({"error": "Format de fichier invalide (seuls .csv et .pdf autorisés)"}), 400
#route pour Route POST /analyze pour effectuer une analyse automatique depuis un fichier CSV ou PDF
@api_bp.route('/analyze', methods=['POST'])
def analyze():
    try:
        # 🔹 On récupère les infos JSON envoyées par le front
        filename = request.json.get('filename')
        domaine = request.json.get('domaine', 'finance')           # Par défaut : finance
        tache = request.json.get('tache', 'classification')        # Par défaut : classification

        # 🔹 On reconstitue le chemin absolu du fichier
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        


        # 🔹 On détecte automatiquement le type de fichier
        filetype = 'pdf' if filename.lower().endswith('.pdf') else 'csv'

        # 🔹 Extraction + nettoyage standardisé
        df = clean_data(filepath, filetype=filetype)

        # 🔹 Prédiction en fonction du domaine et de la tâche spécifiés
        pred = predict(df, domaine=domaine, tache=tache)

        # 🔹 Transformation en réponse lisible
        result = classify(pred)

        # 🔹 Envoi de la réponse JSON au front-end
        return jsonify(result)

    except Exception as e:
        # 🔥 Gestion des erreurs
        return jsonify({"error": str(e)}), 500



# Route POST /simulate pour simuler un scénario via un plugin métier
@api_bp.route('/simulate', methods=['POST'])
def simulate():
    try:
        payload = request.json                          # Données JSON envoyées par le front
        plugin_name = payload.get("plugin")             # Nom du plugin à appeler
        simulation_params = payload.get("params")       # Paramètres de simulation

        # 🔁 Appel fictif du plugin ici (à remplacer par ta vraie logique plugin plus tard)
        result = {
            "plugin": plugin_name,
            "params_received": simulation_params,
            "result": "Simulation effectuée avec succès (dummy)"
        }

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    



 #Route de test   
@api_bp.route('/', methods=['GET'])
def home():
    return "✅ Flask fonctionne parfaitement !"


#route de test noyau
@api_bp.route('/analyze_fake', methods=['GET'])
def analyze_fake():
    # Appel du moteur de prédiction simulé
    result = predict_dummy()
    return jsonify(result)


