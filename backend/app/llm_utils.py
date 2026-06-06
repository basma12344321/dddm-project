import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_interpretation(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es un expert financier et logistique. "
                        "Tu analyses des données d'entreprises et génères des rapports "
                        "professionnels, clairs et actionnables en français. "
                        "Tes réponses sont structurées, précises et sans jargon inutile."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=1024,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Erreur Groq : {e}")
        return "Interprétation non disponible."