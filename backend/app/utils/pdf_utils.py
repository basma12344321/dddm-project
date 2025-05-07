import pdfplumber
import pandas as pd

def extract_pdf_data(file_path):
    """
    Extrait les tableaux d'un PDF et retourne un DataFrame unique.
    Si plusieurs pages contiennent des tableaux, ils sont concaténés.
    """
    tables = []

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                # Convertir le tableau de la page en DataFrame
                df = pd.DataFrame(table[1:], columns=table[0])  # première ligne = header
                tables.append(df)

    if not tables:
        raise ValueError("Aucun tableau détecté dans le PDF.")

    # Fusionner tous les tableaux en un seul DataFrame
    full_df = pd.concat(tables, ignore_index=True)

    return full_df
