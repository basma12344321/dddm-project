# core_engine.py

import pandas as pd

from app.utils.pdf_utils import extract_pdf_data
from app.core_engine.model_loader import load_model
from app.utils.extractor import extract_to_dataframe


def clean_data(file_path, filetype='csv'):
    df = extract_to_dataframe(file_path, filetype)
    print("DataFrame brut extrait :")
    print(df.head())
    print(f"Shape brute: {df.shape}")
    print(f"Colonnes: {df.columns.tolist()[:10]}...")

    # Détection intelligente du plugin logistique
    if 'Task' in df.columns and 'Duration' in df.columns and 'Deadline' in df.columns:
        print("Mode logistique détecté : on conserve la colonne 'Task'")
        return clean_dataframe(df, keep_columns=['Task'], mode='logistic')
    else:
        return clean_dataframe(df, mode='finance')


def clean_dataframe(df, keep_columns=None, mode='finance'):
    """
    Nettoie un DataFrame extrait depuis un fichier (CSV ou PDF).

    Mode 'finance' : conserve toutes les lignes, laisse les NaN
                     pour que le plugin les gère avec fillna(0).
    Mode 'logistic': supprime les lignes vraiment vides.
    """
    keep_columns = keep_columns or []

    # Supprimer les colonnes 100% vides (toutes NaN)
    df.dropna(how='all', axis=1, inplace=True)

    if mode == 'logistic':
        # Pour la logistique : supprimer les lignes sans aucune valeur
        df.dropna(how='all', axis=0, inplace=True)

        for col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '.', regex=False).str.replace(' ', '', regex=False)
            if col not in keep_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        df.dropna(subset=[c for c in df.columns if c not in keep_columns], how='all', inplace=True)

    else:
        # Pour la finance : NE PAS supprimer les lignes avec NaN
        # Le plugin finance gère lui-même les valeurs manquantes via fillna(0)
        # On ne convertit PAS non plus — le plugin finance le fait avec get_numeric()
        pass

    print(f"Shape après nettoyage ({mode}): {df.shape}")
    print(f"Colonnes après nettoyage: {df.columns.tolist()[:10]}...")

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
    Post-traitement générique : transforme une sortie brute en réponse lisible.
    """
    return {
        "raw": prediction.tolist() if hasattr(prediction, 'tolist') else prediction,
        "label": "positif" if prediction[0] > 0.5 else "négatif",
        "confiance": round(float(prediction[0]), 2)
    }