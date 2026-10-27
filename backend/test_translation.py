
import requests

url = "https://libretranslate.com/languages"

try:
    response = requests.get(url, timeout=20)
    print("HTTP status:", response.status_code)

    if response.ok:
        languages = response.json()
        print("Telugu available:", any(
            lang.get("code") == "te" for lang in languages
        ))
        print("Available languages:", [
            lang.get("code") for lang in languages
        ])
    else:
        print("Service response:", response.text[:500])

except requests.RequestException as error:
    print("Connection error:", error)
