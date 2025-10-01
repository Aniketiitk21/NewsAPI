# NewsLens • India (timeline-first)

A free, lightweight news dashboard:
- Step-by-step UI: **Timeline → Scope → State → Category → Mode**
- National & State news with category filters
- Optional stance badge for **state politics** (Gov≡RulingParty)
- Fast **RSS-first** fetching with optional **Deep** mode

## Run locally

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r ../requirements.txt

uvicorn app:app --host 0.0.0.0 --port 8000
