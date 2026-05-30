import pdfplumber
import pandas as pd

def extract_pdf_data(file_path):
    """
    Extrait un tableau structuré OU des paires clé: valeur depuis un PDF.
    Si aucun tableau détecté, passe en mode lecture texte ligne par ligne.
    """
    tables = []

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            # 1. Essayer d'extraire un tableau structuré
            table = page.extract_table()
            if table:
                df = pd.DataFrame(table[1:], columns=table[0])
                tables.append(df)

        # 2. Si des tableaux ont été trouvés → concaténer et retourner
        if tables:
            full_df = pd.concat(tables, ignore_index=True)
            print("Tableau détecté et extrait depuis le PDF")
            return full_df

        # 3. Sinon : basculer en mode clé: valeur
        data = {}
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                for line in text.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        data[key.strip()] = value.strip()

        if not data:
            raise ValueError(" Aucune donnée détectée dans le PDF (ni tableau, ni clé:valeur).")

        print("Extraction clé: valeur réussie depuis le PDF")
        return pd.DataFrame([data])
