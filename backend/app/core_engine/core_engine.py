# core_engine.py
#pour tester le lien noyau-flask
#def predict_dummy(data=None):
 #   """
  #  Cette fonction simule une prédiction d'un modèle ML.
   # Elle pourrait plus tard utiliser un vrai modèle pour analyser un DataFrame ou des données.
    #"""
#    return {
     #   "prediction": "valorisation positive",
      #  "score": 0.92,
       # "explication": "Basé sur les indicateurs fournis (simulé)."
  #  }

# core_engine.py

import pandas as pd

from app.utils.pdf_utils import extract_pdf_data  # À créer plus tard si besoin

from app.core_engine.model_loader import load_model
from app.utils.extractor import extract_to_dataframe



#arrange le format et nettoie
def clean_data(file_path, filetype='csv'):
    df = extract_to_dataframe(file_path, filetype)
    return clean_dataframe(df)

#à développer plus 
def clean_dataframe(df):
    """
    Nettoie un DataFrame déjà extrait (peu importe son origine).
    """
    df.columns = [col.strip().lower() for col in df.columns]
    df.dropna(inplace=True)
    # Ajouter ici : conversions de types, renommage, filtrage…
    return df




def predict(df, domaine='finance', tache='classification'):
    """
    Utilise le routeur de modèles pour choisir le bon modèle ML
    et produire une prédiction à partir du DataFrame nettoyé.
    """
    model = load_model(domaine, tache)
    prediction = model.predict(df)
    return prediction

def classify(prediction):
    """
    Post-traitement générique (non métier) : peut transformer une sortie brute en réponse lisible.
    Ex : ajouter un label, un niveau, une confiance, etc.
    """
    # Exemples d’interprétation
    return {
        "raw": prediction.tolist() if hasattr(prediction, 'tolist') else prediction,
        "label": "positif" if prediction[0] > 0.5 else "négatif",
        "confiance": round(float(prediction[0]), 2)
    }

