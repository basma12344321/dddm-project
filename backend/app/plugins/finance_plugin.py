from app.plugins.base_plugin import BasePlugin
import joblib
import pandas as pd
import numpy as np
import os
import shap
import xgboost as xgb
from typing import Union, Dict
from app.llm_utils import generate_interpretation


class FinancePlugin(BasePlugin):
    REQUIRED_FIELDS_NORMALIZED = ['ebit', 'revenue']

    def __init__(self, model_path=None):
        # Cherche d'abord le modèle JSON (nouveau format), puis pkl (ancien)
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'models', 'finance'))

        json_path = os.path.join(base_dir, 'regression_model_clean.json')
        pkl_path  = os.path.join(base_dir, 'regression_model.pkl')
        # Priorité au pkl original (R²=0.75) — le clean.json est un fallback

        if model_path is None:
            if os.path.exists(pkl_path):
                model_path = pkl_path
                print(f"Modèle PKL original trouvé (R²=0.75) : {pkl_path}")
            elif os.path.exists(json_path):
                model_path = json_path
                print(f"Modèle JSON trouvé (fallback) : {json_path}")
            else:
                raise ValueError(f"Aucun modèle trouvé dans {base_dir}")

        try:
            if model_path.endswith('.json'):
                # Chargement natif XGBoost — compatible toutes versions SHAP
                self.model = xgb.XGBRegressor()
                self.model.load_model(model_path)
                print(f"Modèle XGBoost chargé depuis JSON : {model_path}")
            else:
                self.model = joblib.load(model_path)
                print(f"Modèle PKL chargé : {model_path}")

            if not hasattr(self.model, 'predict'):
                raise ValueError("Le modèle chargé n'a pas de méthode predict()")

            self._validate_model_features()

        except Exception as e:
            raise ValueError(f"Erreur de chargement du modèle: {str(e)}")

        self.seuil_bas  = 0.05
        self.seuil_haut = 0.15

        # Initialisation SHAP — passer le booster directement évite le bug expected_value string
        try:
            booster = self.model.get_booster()
            self.explainer = shap.TreeExplainer(booster)
            # Vérifier et corriger expected_value si c'est une string
            ev = self.explainer.expected_value
            if isinstance(ev, str):
                import ast
                ev_clean = ev.strip().strip('[]')
                self.explainer.expected_value = float(ev_clean)
                print(f"expected_value corrigé: {self.explainer.expected_value}")
            print("SHAP TreeExplainer initialisé avec succès")
        except Exception as e:
            print(f"Avertissement SHAP: {str(e)}")
            self.explainer = None

        print(f"Plugin Finance initialisé avec modèle: {type(self.model)}")

    def _validate_model_features(self):
        if hasattr(self.model, 'get_booster'):
            self.expected_features = self.model.get_booster().feature_names
        else:
            self.expected_features = []
        print(f"Features attendues par le modèle: {self.expected_features}")

    def _normalize_col_name(self, col: str) -> str:
        return (
            col.strip().lower()
            .replace(' ', '').replace('-', '').replace('_', '').replace('&', '')
        )

    def preprocess(self, data: Union[Dict, pd.DataFrame]) -> pd.DataFrame:
        print("Entree dans preprocess()")

        try:
            if isinstance(data, dict):
                df = pd.DataFrame([data]).reset_index(drop=True)
            else:
                df = data.copy().reset_index(drop=True)

            print(f"Shape initiale: {df.shape}")

            col_norm_map = {self._normalize_col_name(c): c for c in df.columns}

            def get_col(df, *keys):
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

            ebit         = get_numeric(df, 'EBIT', 'ebit')
            revenue      = get_numeric(df, 'Revenue', 'revenue', 'Total Revenue')
            inv_cap      = get_numeric(df, 'Invested Capital', 'investedcapital', 'InvestedCapital')
            fcf          = get_numeric(df, 'Free Cash Flow', 'freecashflow', 'FreeCashFlow')
            total_assets = get_numeric(df, 'Total assets', 'totalassets', 'TotalAssets', 'Total Assets')
            debt_eq      = get_numeric(df, 'Debt to Equity', 'debtequity', 'debtEquityRatio',
                                       'Debt/Equity', 'Debt to Equity')
            market_cap   = get_numeric(df, 'Market Cap', 'marketcap', 'MarketCap')

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

            asset_turnover = pd.Series(
                np.where(total_assets != 0, revenue / total_assets, 0.0),
                index=df.index
            )

            sector_raw = get_col(df, 'Sector_Grouped', 'Sector', 'sector', 'sectorgrouped')
            if sector_raw is not None:
                sector_series = sector_raw.astype(str).str.strip()
            else:
                print("Sector manquant -> ajout 'Other'")
                sector_series = pd.Series(['Other'] * len(df), index=df.index)

            sectors = [
                'Consumer Cyclical', 'Consumer Defensive', 'Energy',
                'Healthcare', 'Industrials', 'Technology'
            ]

            expected_cols = [
                'EBIT', 'Invested Capital', 'Free Cash Flow', 'Asset Turnover',
                'Debt to Equity', 'R&D to Revenue', 'SG&A to Revenue', 'Market Cap',
                'Sector_Consumer Cyclical', 'Sector_Consumer Defensive',
                'Sector_Energy', 'Sector_Healthcare',
                'Sector_Industrials', 'Sector_Other', 'Sector_Technology'
            ]

            data_dict = {
                'EBIT':             ebit.values,
                'Invested Capital': inv_cap.values,
                'Free Cash Flow':   fcf.values,
                'Asset Turnover':   asset_turnover.values,
                'Debt to Equity':   debt_eq.values,
                'R&D to Revenue':   rd_to_rev.values,
                'SG&A to Revenue':  sga_to_rev.values,
                'Market Cap':       market_cap.values,
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

    def _compute_shap(self, df: pd.DataFrame) -> Dict:
        if self.explainer is None:
            return {}

        try:
            shap_values = self.explainer.shap_values(df)

            # Compatibilité SHAP 0.40+ : Explanation object ou ndarray
            if hasattr(shap_values, 'values'):
                raw = np.array(shap_values.values)
            else:
                raw = np.array(shap_values)

            # Normaliser la forme : on veut (n_samples, n_features)
            if raw.ndim == 1:
                shap_row = raw
            elif raw.ndim == 2:
                shap_row = raw[0]
            elif raw.ndim == 3:
                shap_row = raw[0, :, 0]
            else:
                shap_row = raw.flatten()[:len(df.columns)]

            print(f"SHAP raw shape: {raw.shape}, row shape: {shap_row.shape}")

            feature_names = df.columns.tolist()

            shap_data = []
            for i, feature in enumerate(feature_names):
                if not feature.startswith('Sector_') and i < len(shap_row):
                    val = float(shap_row[i])
                    shap_data.append({
                        'feature': feature,
                        'shap_value': round(val, 6),
                        'feature_value': round(float(df[feature].iloc[0]), 4),
                        'impact': 'positif' if val > 0 else 'negatif',
                        'abs_impact': abs(val)
                    })

            shap_data.sort(key=lambda x: x['abs_impact'], reverse=True)
            top_features = shap_data[:5]

            explanation = self._generate_shap_explanation(top_features)

            # Base value — robuste toutes versions
            try:
                ev = self.explainer.expected_value
                if hasattr(ev, '__len__'):
                    base_value = float(ev[0])
                else:
                    base_value = float(ev)
            except Exception:
                base_value = 0.0

            print(f"SHAP calculé avec succès : {len(top_features)} features principales")

            return {
                'shap_values': shap_data,
                'top_features': top_features,
                'explanation': explanation,
                'base_value': round(base_value, 4)
            }

        except Exception as e:
            print(f"Erreur calcul SHAP: {str(e)}")
            import traceback
            traceback.print_exc()
            return {}

    def _generate_shap_explanation(self, top_features: list) -> str:
        if not top_features:
            return "Explication non disponible."

        lines = []
        for f in top_features:
            direction = "augmente" if f['impact'] == 'positif' else "diminue"
            lines.append(
                f"• {f['feature']} (valeur: {f['feature_value']}) "
                f"→ {direction} le ROIC de {abs(f['shap_value']):.4f}"
            )
        return "\n".join(lines)

    def interpret(self, raw_output, df_preprocessed: pd.DataFrame = None) -> Dict:
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

        shap_info = ""
        if df_preprocessed is not None:
            shap_result = self._compute_shap(df_preprocessed)
            if shap_result and shap_result.get('top_features'):
                shap_info = "\n".join([
                    f"- {f['feature']}: impact {'positif' if f['impact'] == 'positif' else 'négatif'} de {abs(f['shap_value']):.4f}"
                    for f in shap_result['top_features']
                ])

        prompt = f"""Tu es un expert financier. Génère un rapport professionnel et complet en français.

        ROIC prédit : {result['roic']*100:.2f}%
        Niveau : {niveau}

        Facteurs clés (SHAP) :
        {shap_info if shap_info else "Non disponible"}

        Structure obligatoire (complète chaque section entièrement) :
        1. Interprétation du ROIC
        2. Points forts et points faibles
        3. Recommandation concrète

        Important : termine chaque phrase et chaque section complètement, ne coupe pas le texte."""
        result["interpretation_ia"] = generate_interpretation(prompt)

        if df_preprocessed is not None:
            shap_result = self._compute_shap(df_preprocessed)
            if shap_result:
                result["shap"] = shap_result
                print("SHAP ajouté au résultat")

        return result

    def simulate_from_file(self, df: pd.DataFrame) -> Dict:
        df_clean = self.preprocess(df)
        prediction = self._make_prediction(df_clean)
        return self.interpret(prediction, df_clean)

    def simulate(self, scenario: Dict) -> Dict:
        print("Simulation lancee")
        df = self.preprocess(scenario)
        prediction = self._make_prediction(df)
        return self.interpret(prediction, df)

    def schedule(self, data, algorithm="FCFS"):
        print("Scheduling non implemente dans le plugin Finance")
        return None