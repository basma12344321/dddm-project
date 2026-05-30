import os
import joblib

def load_model(domain, task):
    """
    Charge un modèle ML à partir du dossier models/<domain>/.
    
    """

    # 1. Nom du fichier
    model_name = f"{task}_model.pkl"

    # 2. Détermination du chemin de base
    try:
        # Cas : appelé depuis Flask
        from flask import current_app
        
        base_path = os.path.join(current_app.root_path, "app", "models", domain)

    except RuntimeError:
        # Cas : appelé depuis un script normal (test, notebook…)
        base_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "app", "models", domain)
        )

    print(f" Recherche dans: {base_path}")

    # 3. Chemin complet du modèle
    model_path = os.path.join(base_path, model_name)

    # 4. Vérifications
    if not os.path.exists(base_path):
        raise FileNotFoundError(
            f"Dossier '{domain}' introuvable dans {base_path}\n"
            f"→ Vérifie que le dossier existe bien."
        )

    if not os.path.exists(model_path):
        available = [f for f in os.listdir(base_path) if f.endswith('.pkl')]
        raise FileNotFoundError(
            f"Modèle '{model_name}' introuvable dans {base_path}.\n"
            f"fichiers disponibles : {available}"
        )

    # 5. Chargement
    print(f" Chargement du modèle : {model_name}")
    return joblib.load(model_path)
