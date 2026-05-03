import requests
from django.conf import settings

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openrouter/free"


def ask_ai(question, data):
    api_key = getattr(settings, "OPENROUTER_API_KEY", None)

    if not api_key:
        return "Clé API IA manquante. Vérifiez votre fichier .env."

    prompt = f"""
Tu es un assistant IA pour School Manager.

RÈGLES STRICTES:
- Ne jamais utiliser de tableaux.
- Répondre uniquement en texte clair.
- Utiliser des listes simples avec tirets (-) si nécessaire.
- Ne pas utiliser de Markdown complexe.
- Utiliser uniquement la devise DZD.
- Ne pas inventer de données.
- Si une information semble incohérente, signale-le clairement.

Données:
{data}

Question:
{question}

Structure obligatoire:
1. Analyse
2. Recommandations
3. Conclusion
"""

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.4,
                "max_tokens": 700,
            },
            timeout=30,
        )

        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]

    except requests.exceptions.HTTPError:
        return f"Erreur API IA : {response.status_code} - {response.text[:300]}"

    except requests.exceptions.RequestException:
        return "Erreur de connexion à l’API IA. Vérifiez votre connexion internet."

    except Exception:
        return "Erreur inattendue lors de la génération de la réponse IA."