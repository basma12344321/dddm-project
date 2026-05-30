import os
import requests

# Clé API Anthropic - à définir dans les variables d'environnement
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

def generate_interpretation(prompt: str) -> str:
    """
    Génère une interprétation textuelle via l'API Claude (Anthropic).
    Rapide, multilingue, et bien plus précis que BloomZ pour les analyses financières.
    """
    if not ANTHROPIC_API_KEY:
        return _fallback_interpretation(prompt)

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-haiku-4-5-20251001",  # Modèle le plus rapide et économique
                "max_tokens": 200,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "system": (
                    "Tu es un expert financier. Réponds en français, "
                    "de manière concise (2-3 phrases max), claire et professionnelle. "
                    "Pas de markdown, pas de listes, juste du texte simple."
                )
            },
            timeout=15  # timeout 15 secondes max
        )

        if response.status_code == 200:
            data = response.json()
            return data["content"][0]["text"].strip()
        else:
            print(f"Erreur API Claude: {response.status_code} - {response.text}")
            return _fallback_interpretation(prompt)

    except Exception as e:
        print(f"Erreur generate_interpretation: {str(e)}")
        return _fallback_interpretation(prompt)


def _fallback_interpretation(prompt: str) -> str:
    """
    Interprétation de secours basée sur des règles simples,
    utilisée si l'API Claude n'est pas disponible.
    """
    prompt_lower = prompt.lower()

    if "faible" in prompt_lower:
        return (
            "Le ROIC faible indique que l'entreprise génère peu de valeur "
            "par rapport aux capitaux investis. Une révision de la stratégie "
            "d'allocation des ressources est recommandée."
        )
    elif "moyenne" in prompt_lower or "correcte" in prompt_lower:
        return (
            "Le ROIC moyen reflète une rentabilité acceptable mais perfectible. "
            "L'entreprise crée de la valeur sans pour autant figurer parmi "
            "les leaders de son secteur."
        )
    elif "élevée" in prompt_lower or "elevee" in prompt_lower or "bonne" in prompt_lower:
        return (
            "Le ROIC élevé traduit une excellente capacité à générer de la valeur "
            "à partir des capitaux investis. L'entreprise se positionne favorablement "
            "par rapport à ses concurrents."
        )
    else:
        return "Analyse financière effectuée avec succès."