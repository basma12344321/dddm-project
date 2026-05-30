from flask import Blueprint, request, jsonify, current_app
import os
import math
import pandas as pd
import traceback

from app.core_engine.core_engine import clean_data
from app.core_engine.plugin_loader import load_plugin

api_bp = Blueprint('api', __name__)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def sanitize_for_json(obj):
    """
    Remplace récursivement NaN et Infinity par None (null en JSON).
    Évite le bug 'NaN is not valid JSON' côté Angular.
    """
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(i) for i in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    else:
        return obj


@api_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if allowed_file(file.filename):
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
        print(f"Tentative de sauvegarde dans : {filepath}")
        try:
            file.save(filepath)
            print("Fichier bien sauvegarde !")
        except Exception as e:
            print("Erreur pendant la sauvegarde :", e)

        return jsonify({"message": f"Fichier {file.filename} bien recu."}), 200
    else:
        return jsonify({"error": "Format de fichier invalide (seuls .csv et .pdf autorises)"}), 400


@api_bp.route('/analyze', methods=['POST'])
def analyze():
    print("\n=== Requete recue sur /analyze ===")

    if not request.is_json:
        return jsonify({
            "error": "Unsupported Media Type",
            "message": "Content-Type must be application/json"
        }), 415

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Empty JSON body"}), 400

        required_fields = ['filename', 'tache', 'domaine']
        missing_fields = [f for f in required_fields if f not in data]
        if missing_fields:
            return jsonify({"error": "Missing required fields", "missing": missing_fields}), 400

        filename = data['filename']
        tache = data['tache']
        domaine = data['domaine']

        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            return jsonify({"error": "Fichier non trouve", "path": filepath}), 404

        filetype = 'pdf' if filename.lower().endswith('.pdf') else 'csv'

        df_raw = clean_data(filepath, filetype=filetype)
        plugin = load_plugin(domaine)

        if domaine == 'logistic':
            print("Analyse specifique du plugin logistique")
            raw_result = plugin.schedule(df_raw)
            result = plugin.interpret(raw_result)
        else:
            df_clean = plugin.preprocess(df_raw)
            prediction = plugin._make_prediction(df_clean)
            result = plugin.interpret(prediction)

        # ✅ Ajout de input_data avec NaN nettoyés
        if isinstance(df_raw, pd.DataFrame) and not df_raw.empty:
            try:
                input_dict = df_raw.iloc[0].to_dict()
                result["input_data"] = sanitize_for_json(input_dict)
            except Exception as e:
                print("Impossible d'ajouter input_data :", str(e))
                result["input_data"] = {}

        # ✅ Nettoyage complet du résultat avant sérialisation JSON
        result = sanitize_for_json(result)

        return jsonify(result)

    except Exception as e:
        print("Erreur pendant l'analyse :")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api_bp.route('/simulate', methods=['POST'])
def simulate():
    print("Entree confirmee dans la route /simulate")
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Invalid JSON data"}), 400

    plugin_name = payload.get("plugin")
    scenario = payload.get("params", {})

    if not plugin_name:
        return jsonify({"error": "Missing required parameter: 'plugin'"}), 400
    if not scenario:
        return jsonify({"error": "Missing or empty 'params' object"}), 400

    try:
        plugin = load_plugin(plugin_name)
        result = plugin.simulate(scenario)
        result = sanitize_for_json(result)
        return jsonify(result)
    except Exception as e:
        print(f"Erreur dans plugin.simulate(): {str(e)}")
        return jsonify({"error": f"Simulation failed: {str(e)}"}), 500


@api_bp.route("/schedule", methods=["POST"])
def schedule():
    data = request.get_json()
    plugin_name = data.get("plugin")
    scenario = data.get("scenario")

    if not plugin_name or not scenario:
        return jsonify({"error": "Missing plugin or scenario"}), 400

    plugin = load_plugin(plugin_name)

    try:
        result = plugin.schedule(scenario)
        interpreted = plugin.interpret(result)
        interpreted = sanitize_for_json(interpreted)
        return jsonify(interpreted)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route('/dashboard-data', methods=['GET'])
def dashboard_data():
    print("\nRoute /dashboard-data appelee")

    try:
        data_path = os.path.join(current_app.root_path, 'data', 'df_final.csv')
        print(f"Lecture du fichier : {data_path}")
        df = pd.read_csv(data_path)

        if df.empty:
            return jsonify({'error': 'df_final.csv is empty'}), 400
        if 'Sector_Grouped' not in df.columns:
            return jsonify({'error': 'Colonne Sector_Grouped absente'}), 400

        secteur = df['Sector_Grouped'].iloc[0]

        from app.core_engine.model_loader import load_model
        model = load_model('finance', 'regression')

        df_encoded = df.copy()
        if 'ROIC' in df_encoded.columns:
            df_encoded.drop(columns=['ROIC'], inplace=True)

        sector_columns = [
            'Sector_Consumer Cyclical', 'Sector_Consumer Defensive', 'Sector_Energy',
            'Sector_Healthcare', 'Sector_Industrials', 'Sector_Other', 'Sector_Technology'
        ]
        df_encoded = pd.get_dummies(df_encoded, columns=['Sector'], prefix='Sector')

        for col in sector_columns:
            if col not in df_encoded.columns:
                df_encoded[col] = 0

        df_encoded = df_encoded[[
            'EBIT', 'Invested Capital', 'Free Cash Flow', 'Asset Turnover',
            'Debt to Equity', 'R&D to Revenue', 'SG&A to Revenue', 'Market Cap'
        ] + sector_columns]

        y_pred = model.predict(df_encoded)
        df['Predicted_ROIC'] = y_pred

        classement = df[df['Sector_Grouped'] == secteur].sort_values(
            'Predicted_ROIC', ascending=False
        ).reset_index(drop=True)

        top = classement.head(10)
        labels = [f"Entreprise {i+1}" for i in top.index]
        values = (top["Predicted_ROIC"] * 100).round(1).tolist()

        entreprise = top.iloc[0]
        secteur_moyenne = classement.mean(numeric_only=True)

        radar_features = [
            'EBIT', 'Invested Capital', 'Free Cash Flow', 'Asset Turnover',
            'Debt to Equity', 'R&D to Revenue', 'SG&A to Revenue', 'Market Cap'
        ]

        radar_data = {
            'labels': radar_features,
            'entreprise': [round(float(entreprise.get(f, 0)), 2) for f in radar_features],
            'secteur': [round(float(secteur_moyenne.get(f, 0)), 2) for f in radar_features],
            'titre': "Comparaison du profil financier (valeurs brutes)"
        }

        response = sanitize_for_json({
            'classement': {
                'labels': labels,
                'values': values,
                'secteur': secteur,
                'titre': "Top 10 des entreprises du secteur selon le ROIC (%)"
            },
            'radar': radar_data
        })

        return jsonify(response)

    except Exception as e:
        print("Erreur dans /dashboard-data :", str(e))
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/', methods=['GET'])
def home():
    return "Flask fonctionne parfaitement !"