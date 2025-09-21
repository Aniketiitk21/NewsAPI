# NewsAPI
My Personal Experiment of Central News Platform
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install newspaper3k feedparser pytz transformers torch lxml[html_clean]
python main.py            # default: last 2 days, heuristic stance
python main.py --days 3   # example: last 3 days
python main.py --use-zero-shot 1   # optional: enable transformers zero-shot
# Windows (PowerShell)
py -m venv .venv
.\.venv\Scripts\Activate
py -m pip install -U pip
py -m pip install newspaper3k feedparser pytz transformers torch lxml[html_clean]
py .\main.py
py .\main.py --days 3
py .\main.py --use-zero-shot 1
