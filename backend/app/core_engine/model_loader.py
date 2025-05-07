
#new
import os
import joblib

def load_model(domain, task):
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'models', domain))
    model_path = os.path.join(base_path, f"{task}_model.pkl")

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}")

    return joblib.load(model_path)
