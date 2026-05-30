import requests

url = "http://localhost:5000/analyze"

payload = {
    "filename": "analyze_test_valid.csv",
    "domaine": "finance",
    "tache": "regression"
}


response = requests.post(url, json=payload)
print(response.json())
