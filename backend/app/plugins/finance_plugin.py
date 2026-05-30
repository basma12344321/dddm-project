from app.plugins.base_plugin import BasePlugin
import joblib
import pandas as pd
import numpy as np
import os
from typing import Union, Dict
from app.llm_utils import generate_interpretation


class FinancePlugin(BasePlugin):
    REQUIRED_FIELDS_NORMALIZED = ['ebit', 'revenue']

    def __init__(self, model_path=None):
        if model_path is None:
            model_path = os.path.abspath(os.path.join(
                os.path.dirname(__file__),
                '..', 'models', 'finance', 'regression_model.pkl'
            ))

        try:
            self.model = joblib.load(model_path)
            if not hasattr(self.model, 'predict'):
                raise ValueError("Le modèle chargé n'a pas de méthode predict()")
            self._validate_model_features()
        except Exception as e:
            raise ValueError(f"Erreur de chargement du modèle: {str(e)}")

        self.seuil_bas = 0.05
        self.seuil_haut = 0.15
        print(f"Plugin Finance initialisé avec modèle: {type(self.model)}")

    def _validate_model_features(self):
        if hasattr(self.model, 'get_booster'):
            self.expected_features = self.model.get_booster().feature_names
        else:
            self.expected_features = []
        print(f"Features attendues par le modèle: {self.expected_features}")

    def _normalize_col_name(self, col: str) -> str:
        """Normalise un nom de colonne : lowercase, sans espaces/tirets/underscores/&"""
        return (
            col.strip().lower()
            .replace(' ', '').replace('-', '').replace('_', '').replace('&', '')
        )

    def preprocess(self, data: Union[Dict, pd.DataFrame]) -> pd.DataFrame:
        print("Entree dans preprocess()")

        try:
            # 1. Convertir en DataFrame avec index propre
            if isinstance(data, dict):
                df = pd.DataFrame([data]).reset_index(drop=True)
            else:
                df = data.copy().reset_index(drop=True)

            print(f"Shape initiale: {df.shape}")

            # 2. Créer un mapping col_normalisée -> col_originale
            col_norm_map = {self._normalize_col_name(c): c for c in df.columns}

            def get_col(df, *keys):
                """Récupère la première colonne trouvée parmi les clés normalisées."""
                for key in keys:
                    norm = self._normalize_col_name(key)
                    if norm in col_norm_map:
                        return df[col_norm_map[norm]]
                return None

            def get_numeric(df, *keys, default=0.0):
                s = get_col(df, *keys)
                if s is None:
                    return pd.Series([default] * len(df), index=df.index)
                return pd.to_numeric(
                    s.astype(str).str.replace(',', '.', regex=False),
                    errors='coerce'
                ).fillna(default)

            # 3. Extraire chaque feature avec plusieurs variantes de noms
            ebit         = get_numeric(df, 'EBIT', 'ebit')
            revenue      = get_numeric(df, 'Revenue', 'revenue', 'Total Revenue')
            inv_cap      = get_numeric(df, 'Invested Capital', 'investedcapital', 'InvestedCapital')
            fcf          = get_numeric(df, 'Free Cash Flow', 'freecashflow', 'FreeCashFlow')
            total_assets = get_numeric(df, 'Total assets', 'totalassets', 'TotalAssets', 'Total Assets')
            debt_eq      = get_numeric(df, 'Debt to Equity', 'debtequity', 'debtEquityRatio',
                                       'Debt/Equity', 'Debt to Equity')
            market_cap   = get_numeric(df, 'Market Cap', 'marketcap', 'MarketCap')

            # R&D to Revenue : ratio direct ou calculé
            rd_to_rev_col = get_col(df, 'R&D to Revenue', 'rdtorevenue', 'RdToRevenue')
            if rd_to_rev_col is not None:
                rd_to_rev = pd.to_numeric(
                    rd_to_rev_col.astype(str).str.replace(',', '.', regex=False),
                    errors='coerce'
                ).fillna(0.0)
            else:
                rd_expenses = get_numeric(df, 'R&D Expenses', 'rdexpenses', 'RdExpenses')
                rd_to_rev = pd.Series(
                    np.where(revenue != 0, rd_expenses / revenue, 0.0),
                    index=df.index
                )

            # SG&A to Revenue : ratio direct ou calculé
            sga_to_rev_col = get_col(df, 'SG&A to Revenue', 'sgatorevenue', 'SgaToRevenue')
            if sga_to_rev_col is not None:
                sga_to_rev = pd.to_numeric(
                    sga_to_rev_col.astype(str).str.replace(',', '.', regex=False),
                    errors='coerce'
                ).fillna(0.0)
            else:
                sga_expenses = get_numeric(df, 'SG&A Expense', 'sgaexpense', 'SgaExpense')
                sga_to_rev = pd.Series(
                    np.where(revenue != 0, sga_expenses / revenue, 0.0),
                    index=df.index
                )

            # Asset Turnover calculé
            asset_turnover = pd.Series(
                np.where(total_assets != 0, revenue / total_assets, 0.0),
                index=df.index
            )

            # 4. Secteur
            sector_raw = get_col(df, 'Sector_Grouped', 'Sector', 'sector', 'sectorgrouped')
            if sector_raw is not None:
                sector_series = sector_raw.astype(str).str.strip()
            else:
                print("Sector manquant -> ajout 'Other'")
                sector_series = pd.Series(['Other'] * len(df), index=df.index)

            # 5. One-hot encoding secteur
            sectors = [
                'Consumer Cyclical', 'Consumer Defensive', 'Energy',
                'Healthcare', 'Industrials', 'Technology'
            ]

            # 6. Construire le DataFrame final en une seule opération (evite fragmentation)
            expected_cols = [
                'EBIT', 'Invested Capital', 'Free Cash Flow', 'Asset Turnover',
                'Debt to Equity', 'R&D to Revenue', 'SG&A to Revenue', 'Market Cap',
                'Sector_Consumer Cyclical', 'Sector_Consumer Defensive',
                'Sector_Energy', 'Sector_Healthcare',
                'Sector_Industrials', 'Sector_Other', 'Sector_Technology'
            ]

            data_dict = {
                'EBIT':              ebit.values,
                'Invested Capital':  inv_cap.values,
                'Free Cash Flow':    fcf.values,
                'Asset Turnover':    asset_turnover.values,
                'Debt to Equity':    debt_eq.values,
                'R&D to Revenue':    rd_to_rev.values,
                'SG&A to Revenue':   sga_to_rev.values,
                'Market Cap':        market_cap.values,
            }

            for sector in sectors:
                data_dict[f'Sector_{sector}'] = (sector_series == sector).astype(int).values

            data_dict['Sector_Other'] = (~sector_series.isin(sectors)).astype(int).values

            df_final = pd.DataFrame(data_dict, columns=expected_cols)

            if df_final.empty:
                raise ValueError("DataFrame vide apres preprocessing")

            print("DataFrame FINAL pret pour le modele:")
            print(df_final.head())

            return df_final

        except Exception as e:
            print(f"Erreur preprocess: {str(e)}")
            raise

    def _make_prediction(self, df: pd.DataFrame) -> float:
        if df.empty:
            raise ValueError("Le DataFrame est vide")

        y_pred = self.model.predict(df)

        if len(y_pred) == 0:
            raise ValueError("Le modele a retourne un resultat vide")

        return float(y_pred[0])

    def interpret(self, raw_output: float) -> Dict:
        roic = raw_output

        if roic < self.seuil_bas:
            niveau = "faible"
            commentaire = "Rentabilite faible."
        elif roic < self.seuil_haut:
            niveau = "moyenne"
            commentaire = "Rentabilite correcte."
        else:
            niveau = "elevee"
            commentaire = "Bonne rentabilite."

        result = {
            "roic": round(roic, 4),
            "niveau": niveau,
            "commentaire": commentaire
        }

        prompt = f"Explique un ROIC de {result['roic']} ({niveau}) simplement."
        result["interpretation_ia"] = generate_interpretation(prompt)

        return result

    def simulate_from_file(self, df: pd.DataFrame) -> Dict:
        df_clean = self.preprocess(df)
        prediction = self._make_prediction(df_clean)
        return self.interpret(prediction)

    def simulate(self, scenario: Dict) -> Dict:
        print("Simulation lancee")
        df = self.preprocess(scenario)
        prediction = self._make_prediction(df)
        return self.interpret(prediction)

    def schedule(self, data, algorithm="FCFS"):
        print("Scheduling non implemente dans le plugin Finance")
        return None
