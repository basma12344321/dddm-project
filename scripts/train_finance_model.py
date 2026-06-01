# scripts/train_finance_model.py

import os
import sys
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import yfinance as yf
import joblib
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# ─── Configuration ────────────────────────────────────────────────────────────

# ✅ Financials exclus — ROIC incompatible avec les autres secteurs
TICKERS_BY_SECTOR = {
    'Technology': [
        'AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA', 'INTC', 'AMD', 'ORCL',
        'CRM', 'ADBE', 'CSCO', 'IBM', 'QCOM', 'TXN', 'NOW', 'SNOW', 'PLTR',
        'SHOP', 'SQ', 'PYPL', 'NFLX', 'TWLO', 'NET', 'DDOG', 'MDB',
        'CRWD', 'ZS', 'PANW', 'FTNT', 'CTSH', 'ACN', 'INFY',
        'HPQ', 'HPE', 'DELL', 'AMAT', 'LRCX', 'KLAC',
    ],
    'Consumer Defensive': [
        'PG', 'KO', 'PEP', 'WMT', 'COST', 'CL', 'GIS', 'MKC', 'SJM', 'CHD',
        'KMB', 'CLX', 'HSY', 'CPB', 'CAG', 'HRL', 'MO', 'PM',
        'BG', 'ADM', 'TSN', 'KR', 'SFM',
    ],
    'Consumer Cyclical': [
        'AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'SBUX', 'TGT', 'LOW', 'GM', 'F',
        'BKNG', 'ABNB', 'MAR', 'HLT', 'DIS', 'CMCSA',
        'EBAY', 'ETSY', 'TJX', 'ROST', 'BURL',
    ],
    'Healthcare': [
        'JNJ', 'PFE', 'UNH', 'MRK', 'ABBV', 'TMO', 'ABT', 'DHR', 'BMY', 'LLY',
        'AMGN', 'GILD', 'BIIB', 'REGN', 'VRTX', 'MRNA',
        'CVS', 'CI', 'HUM', 'BSX', 'SYK', 'MDT', 'BDX', 'ISRG',
        'IDXX', 'WAT', 'A',
    ],
    'Industrials': [
        'GE', 'HON', 'MMM', 'CAT', 'BA', 'UPS', 'FDX', 'RTX', 'LMT', 'DE',
        'EMR', 'ETN', 'ROK', 'PH', 'ITW', 'DOV', 'CARR', 'OTIS',
        'TT', 'JCI', 'AME', 'FAST', 'GWW', 'EXPD', 'CHRW', 'ODFL',
    ],
    'Energy': [
        'XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'VLO', 'PSX', 'OXY', 'HAL',
        'BKR', 'DVN', 'APA', 'CTRA', 'CNX', 'AR', 'EQT', 'RRC',
        'KMI', 'WMB', 'OKE', 'EPD', 'MPLX', 'TRGP',
    ],
}

PROJECT_ROOT    = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MODEL_SAVE_PATH = os.path.join(PROJECT_ROOT, 'backend', 'app', 'models', 'finance')
DATA_SAVE_PATH  = os.path.join(PROJECT_ROOT, 'backend', 'app', 'data')

os.makedirs(MODEL_SAVE_PATH, exist_ok=True)
os.makedirs(DATA_SAVE_PATH, exist_ok=True)

# ─── Fetch ────────────────────────────────────────────────────────────────────

def fetch_financials(ticker_symbol: str, sector: str) -> dict | None:
    try:
        ticker = yf.Ticker(ticker_symbol)
        info   = ticker.info

        if not info or len(info) < 10:
            return None

        revenue       = info.get('totalRevenue',     0) or 0
        net_income    = info.get('netIncomeToCommon', 0) or 0
        ebitda        = info.get('ebitda',            0) or 0
        total_assets  = info.get('totalAssets',       None)
        fcf           = info.get('freeCashflow',      0) or 0
        market_cap    = info.get('marketCap',         0) or 0
        debt_eq       = info.get('debtToEquity',      0) or 0
        gross_profit  = info.get('grossProfits',      0) or 0
        op_margins    = info.get('operatingMargins',  0) or 0
        profit_margin = info.get('profitMargins',     0) or 0
        rev_growth    = info.get('revenueGrowth',     0) or 0
        earn_growth   = info.get('earningsGrowth',    0) or 0
        roe           = info.get('returnOnEquity',    0) or 0
        roa           = info.get('returnOnAssets',    0) or 0
        total_debt    = info.get('totalDebt',         0) or 0
        book_value    = info.get('bookValue',         0) or 0
        shares_out    = info.get('sharesOutstanding', 0) or 0

        if revenue == 0:
            return None

        ebit         = revenue * op_margins if op_margins else ebitda * 0.85
        invested_cap = total_debt + (book_value * shares_out) if shares_out else total_debt
        if invested_cap == 0:
            invested_cap = market_cap * 0.3

        if total_assets is None or total_assets == 0:
            total_assets = invested_cap * 1.5

        roic = net_income / invested_cap if invested_cap != 0 else 0

        # ✅ Filtre plus strict sur les outliers
        if abs(roic) > 2 or revenue < 1e6:
            return None

        asset_turnover = revenue / total_assets if total_assets != 0 else 0
        debt_eq_ratio  = debt_eq / 100 if debt_eq > 10 else debt_eq
        sga_to_rev     = max(0, (revenue - gross_profit - ebit) / revenue) if revenue != 0 else 0

        return {
            'ticker':         ticker_symbol,
            'EBIT':           ebit,
            'Invested Capital': invested_cap,
            'Free Cash Flow': fcf,
            'Asset Turnover': asset_turnover,
            'Debt to Equity': debt_eq_ratio,
            'R&D to Revenue': 0.0,
            'SG&A to Revenue': sga_to_rev,
            'Market Cap':     market_cap,
            'Sector':         sector,
            'Sector_Grouped': sector,
            'ROIC':           roic,
            'ROE':            roe,
            'ROA':            roa,
            'Profit Margin':  profit_margin,
            'Revenue Growth': rev_growth,
            'Earnings Growth': earn_growth,
        }

    except Exception as e:
        print(f"Erreur {ticker_symbol}: {str(e)[:50]}")
        return None


def build_dataset() -> pd.DataFrame:
    records = []
    total   = sum(len(v) for v in TICKERS_BY_SECTOR.values())
    count   = 0

    for sector, tickers in TICKERS_BY_SECTOR.items():
        print(f"\nSecteur: {sector}")
        for ticker in tickers:
            count += 1
            print(f"  [{count}/{total}] {ticker}...", end=' ', flush=True)
            record = fetch_financials(ticker, sector)
            if record:
                records.append(record)
                print(f"OK (ROIC={record['ROIC']:.3f})")
            else:
                print("ignoré")

    df = pd.DataFrame(records)
    print(f"\nDataset : {len(df)} entreprises valides sur {total}")
    return df


def preprocess_dataset(df: pd.DataFrame):
    sectors = [
        'Consumer Cyclical', 'Consumer Defensive', 'Energy',
        'Healthcare', 'Industrials', 'Technology'
    ]

    for sector in sectors:
        df[f'Sector_{sector}'] = (df['Sector'] == sector).astype(int)
    df['Sector_Other'] = (~df['Sector'].isin(sectors)).astype(int)

    feature_cols = [
        'EBIT', 'Invested Capital', 'Free Cash Flow', 'Asset Turnover',
        'Debt to Equity', 'R&D to Revenue', 'SG&A to Revenue', 'Market Cap',
        'Sector_Consumer Cyclical', 'Sector_Consumer Defensive',
        'Sector_Energy', 'Sector_Healthcare',
        'Sector_Industrials', 'Sector_Other', 'Sector_Technology'
    ]

    X = df[feature_cols].fillna(0)
    y = df['ROIC']
    return X, y, feature_cols


def train_model(X: pd.DataFrame, y: pd.Series) -> XGBRegressor:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = XGBRegressor(
        n_estimators=500,
        max_depth=4,
        learning_rate=0.02,
        subsample=0.8,
        colsample_bytree=0.7,
        min_child_weight=5,
        gamma=0.2,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae  = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2   = r2_score(y_test, y_pred)

    print(f"\nMétriques du nouveau modèle :")
    print(f"  MAE  : {mae:.4f}")
    print(f"  RMSE : {rmse:.4f}")
    print(f"  R²   : {r2:.4f}")

    # Cross-validation
    cv_scores = cross_val_score(model, X, y, cv=5, scoring='r2')
    print(f"  R² CV : {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

    return model


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 60)
    print("  Réentraînement modèle Finance — ~165 tickers yfinance")
    print("=" * 60)

    print("\n[1/4] Téléchargement données yfinance...")
    df = build_dataset()

    if len(df) < 20:
        print("Pas assez de données. Vérifiez votre connexion.")
        sys.exit(1)

    csv_path = os.path.join(DATA_SAVE_PATH, 'df_final.csv')
    df.to_csv(csv_path, index=False)
    print(f"\n[2/4] Dataset sauvegardé : {csv_path} ({len(df)} lignes)")

    print("\n[3/4] Prétraitement...")
    X, y, feature_cols = preprocess_dataset(df)
    print(f"  Shape X : {X.shape}")

    print("\n[4/4] Entraînement XGBoost...")
    model = train_model(X, y)

    model_path = os.path.join(MODEL_SAVE_PATH, 'regression_model.pkl')
    joblib.dump(model, model_path)
    print(f"\nModèle sauvegardé : {model_path}")
    print("\nRéentraînement terminé avec succès !")