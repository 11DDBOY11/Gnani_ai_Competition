import httpx
from bs4 import BeautifulSoup

url = "https://ppqs.gov.in/advisories-section"
try:
    r = httpx.get(url, timeout=15.0, verify=False)
    soup = BeautifulSoup(r.text, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a['href']
        text = a.get_text().strip()
        if any(w in text.lower() or w in href.lower() for w in ['rice', 'paddy', 'coconut', 'arecanut', 'blast', 'folder']):
            print(f"Text: {text} -> {href}")
except Exception as e:
    print("Error:", e)

