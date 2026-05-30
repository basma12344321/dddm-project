import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib
import os

# Données fictives
df = pd.DataFrame({
    'revenu': [100, 200, 300, 400],
    'dette': [50, 80, 120, 150],
    'label': [0, 1, 1, 0]
})

X = df[['revenu', 'dette']]
y = df['label']

clf = RandomForestClassifier()
clf.fit(X, y)

#  Chemin absolu depuis le dossier scripts/
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
save_path = os.path.join(project_root, 'backend', 'app', 'models', 'finance')
os.makedirs(save_path, exist_ok=True)

# Sauvegarde
joblib.dump(clf, os.path.join(save_path, 'classification_model.pkl'))
print(" Modèle dummy entraîné et sauvegardé avec succès.")
