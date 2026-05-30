import os
import pandas as pd
import requests
import json

# Configuration
API_URL = "http://127.0.0.1:5000/simulate"
#DATA_DIR = "../data"
#DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend', 'data'))

os.makedirs(DATA_DIR, exist_ok=True)

# 1. Préparation des données de test
test_data = {
    "EBIT": 1_000_000,
    "Revenue": 10_000_000,
    "Total assets": 12_000_000,
    "R&D Expenses": 300_00,
    "SG&A Expense": 800_000,
    "Debt to Equity": 0.5,
    "Market Cap": 1_000_000,
    "Sector_Grouped": "Technology",  # Champ obligatoire pour le plugin
    "Invested Capital": 12_000_000,  # Autre champ important
    "Free Cash Flow": 400
}

# 2. Sauvegarde en CSV (pour d'éventuels tests manuels)
pd.DataFrame([test_data]).to_csv(f"{DATA_DIR}/simulate_input.csv", index=False)

# 3. Appel API avec structure complète
payload = {
    "plugin": "finance",
    "params": test_data  # Tous les champs nécessaires au plugin
}

try:
    print(" Envoi de la requête de test...")
    response = requests.post(
        API_URL,
        json=payload,
        headers={'Content-Type': 'application/json'}
    )
    
    print("\n Résultats:")
    print(f"Status Code: {response.status_code}")
    
    try:
        print("Réponse JSON:", response.json())
    except ValueError:
        print("Réponse brute:", response.text)

except requests.exceptions.RequestException as e:
    print(f"\n Erreur de connexion: {str(e)}")

if response.status_code == 200:
    res = response.json()
    #print("\n🟢 Résultat simulé :")
    #print(f"  🔹 ROIC : {res.get('roic')}")
    #print(f"  🔹 Niveau : {res.get('niveau')}")
    #print(f"  🔹 Commentaire : {res.get('commentaire')}")
    #print(f"  🧠 Interprétation IA :\n{res.get('interpretation_ia')}")
else:
    print("❌ Erreur :", response.text)