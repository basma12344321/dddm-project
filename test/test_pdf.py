from backend.app.core_engine.core_engine import clean_data, predict, classify

# Chemin relatif depuis la racine
file_path = "data/test_pdf.pdf"
file_type = "pdf"
domaine = "finance"
tache = "classification"

# Étape 1 : extraction + nettoyage
df = clean_data(file_path, filetype=file_type)
print("✅ Données extraites et nettoyées :")
print(df)

# Étape 2 : prédiction
pred = predict(df, domaine=domaine, tache=tache)

# Étape 3 : post-traitement (ex: classification)
result = classify(pred)

# Résultat final
print("\n✅ Résultat final :")
print(result)
