# test_yfinance.py - à mettre à la racine du projet
import yfinance as yf
ticker = yf.Ticker('AAPL')
info = ticker.info
print("Clés disponibles:")
for k, v in info.items():
    if v is not None and v != 0:
        print(f"  {k}: {v}")