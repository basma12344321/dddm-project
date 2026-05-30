from finance import FinancePlugin  

test_input = {
    "EBIT": 1_000_000,
    "Invested Capital": 8_000_000,
    "Free Cash Flow": 400_000,
    "Revenue": 10_000_000,
    "Total assets": 12_000_000,
    "R&D Expenses": 300_000,
    "SG&A Expense": 800_000,
    "Debt to Equity": 0.5,
    "Market Cap": 15_000_000,
    "Sector_Grouped": "Technology"
}

plugin = FinancePlugin()
df = plugin.preprocess(test_input)
roic_pred = plugin.model.predict(df)[0]
interpretation = plugin.interpret(roic_pred)

print("\n=== Résultat du test FinancePlugin ===")
print(f"ROIC prédit : {roic_pred:.4f}")
print("Interprétation :", interpretation)
