import requests

url = "http://localhost:5000/analyze"
payload = {
    "filename": "test_pdf.pdf",
    "domaine": "finance",
    "tache": "classification"
}

response = requests.post(url, json=payload)
print(response.json())
