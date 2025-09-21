# AP Political News Analyzer

Fetches **Andhra Pradesh political news** (last N days) from multiple sources, applies strict AP filtering, summarizes articles, and classifies **TDP stance** (positive/negative/neutral).  
Generates a clean **dark-themed HTML report**.

---

## ⚙️ Setup & Installation

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install newspaper3k feedparser pytz transformers torch lxml[html_clean]
### Windows (PowerShell)
py -m venv .venv
.\.venv\Scripts\Activate
py -m pip install -U pip
py -m pip install newspaper3k feedparser pytz transformers torch lxml[html_clean]
python main.py --use-zero-shot 1
python main.py --days 3
