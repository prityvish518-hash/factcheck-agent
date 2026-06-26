# FactCheck Agent 🔍

A web app that reads a PDF, finds all factual claims, and checks each one for accuracy using AI.

## Live App
🔗 https://factcheck-agent-rr2ounruy2wcca2uerpfvz.streamlit.app

## What It Does
- Upload any PDF
- Extracts stats, dates, figures, rankings
- Verifies each claim: ✅ Verified / ⚠️ Inaccurate / ❌ False
- Shows corrected facts for wrong claims

## Tech Stack
- Streamlit (frontend)
- Google Gemini API (AI verification)
- PyPDF2 (PDF reading)

## Run Locally
```bash
git clone https://github.com/prityvish518-hash/factcheck-agent.git
cd factcheck-agent
pip install -r requirements.txt
streamlit run app.py
```

Add your Gemini API key in Streamlit secrets:
```
GEMINI_API_KEY = "your-key-here"
```

## License
MIT
