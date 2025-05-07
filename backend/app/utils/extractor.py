import pandas as pd

from app.utils.pdf_utils import extract_pdf_data

def extract_to_dataframe(file_path, filetype='csv'):
    """
    Extrait un DataFrame depuis un fichier selon son type (pdf, csv…).
    """
    if filetype.lower() == 'csv':
        try:
            return pd.read_csv(file_path)
        except Exception as e:
            print(f"[ERREUR] Échec de lecture CSV : {e}")
            return pd.DataFrame()

    elif filetype.lower() == 'pdf':
        return extract_pdf_data(file_path)

    else:
        raise ValueError(f"Format de fichier non supporté : {filetype}")
