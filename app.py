import streamlit as st
import PyPDF2
import json
import io
import time
import requests

st.set_page_config(
    page_title="FactCheck Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  .stApp { background: #0d0f14; color: #e2e8f0; }
  .hero-title {
    font-size: 2.8rem; font-weight: 700; letter-spacing: -0.03em;
    background: linear-gradient(135deg, #e2e8f0 30%, #6ee7b7 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
  }
  .hero-sub { font-size: 1.05rem; color: #64748b; margin-bottom: 2rem; }
  .claim-card {
    background: #141720; border: 1px solid #1e2330;
    border-radius: 12px; padding: 1.2rem 1.4rem; margin-bottom: 1rem;
  }
  .badge {
    display: inline-block; font-size: 0.72rem; font-weight: 600;
    padding: 3px 10px; border-radius: 999px; letter-spacing: 0.05em;
    text-transform: uppercase; font-family: 'JetBrains Mono', monospace;
  }
  .badge-verified   { background: #052e16; color: #6ee7b7; border: 1px solid #16a34a; }
  .badge-inaccurate { background: #2d1b00; color: #fbbf24; border: 1px solid #d97706; }
  .badge-false      { background: #1f0a0a; color: #f87171; border: 1px solid #dc2626; }
  .claim-text   { font-size: 0.97rem; color: #cbd5e1; margin: 0.6rem 0 0.4rem; font-weight: 500; }
  .verdict-text { font-size: 0.88rem; color: #94a3b8; line-height: 1.6; }
  .correct-fact { font-size: 0.88rem; color: #6ee7b7; margin-top: 0.4rem; }
  .summary-bar {
    background: #141720; border: 1px solid #1e2330;
    border-radius: 12px; padding: 1.2rem 1.6rem;
    display: flex; gap: 2rem; margin-bottom: 2rem;
  }
  .stat-num   { font-size: 1.6rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }
  .stat-label { font-size: 0.75rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.08em; }
  .upload-hint { font-size: 0.82rem; color: #475569; margin-top: 0.5rem; }
  div[data-testid="stFileUploader"] {
    background: #141720; border: 2px dashed #1e2330; border-radius: 12px; padding: 1rem;
  }
  .stButton > button {
    background: #6ee7b7; color: #0d0f14; font-weight: 600;
    border: none; border-radius: 8px; padding: 0.6rem 2rem;
    font-family: 'Inter', sans-serif; font-size: 0.95rem;
  }
  .step-label { font-size: 0.8rem; color: #64748b; font-family: 'JetBrains Mono', monospace; margin-bottom: 0.3rem; }
</style>
""", unsafe_allow_html=True)


def call_gemini(prompt, api_key):
    """Call Gemini 2.0 Flash - free tier."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2000}
    }
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def extract_text_from_pdf(uploaded_file):
    reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_claims(text, api_key):
    prompt = f"""Read the text below and find every specific, verifiable claim.
Look for: statistics, percentages, financial figures, dates, rankings, technical specs.

Return ONLY a JSON array, no explanation, no markdown. Each item:
{{
  "id": 1,
  "claim": "<exact claim from document>",
  "category": "stat | date | financial | technical | ranking | other"
}}

Find up to 10 most checkable claims.

TEXT:
{text[:6000]}"""

    raw = call_gemini(prompt, api_key)
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def verify_claim(claim, api_key):
    prompt = f"""You are a fact-checker. Verify this claim using your knowledge.

CLAIM: "{claim['claim']}"
TYPE: {claim['category']}

Respond ONLY with this JSON, no extra text:
{{
  "verdict": "Verified" | "Inaccurate" | "False",
  "confidence": "High" | "Medium" | "Low",
  "explanation": "<1-2 sentences on what you found>",
  "correct_fact": "<real current fact if wrong, else null>",
  "source": "<what source backs this>"
}}

Verified = matches current data. Inaccurate = outdated or off. False = fabricated or contradicted."""

    raw = call_gemini(prompt, api_key)
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        result = json.loads(raw)
    except Exception:
        result = {"verdict": "False", "confidence": "Low",
                  "explanation": "Could not verify.", "correct_fact": None, "source": "N/A"}
    return {**claim, **result}


def render_claim_card(c):
    verdict = c.get("verdict", "Checking…")
    badge_cls = {"Verified": "badge-verified", "Inaccurate": "badge-inaccurate", "False": "badge-false"}.get(verdict, "badge-verified")
    icon = {"Verified": "✓", "Inaccurate": "⚠", "False": "✗"}.get(verdict, "…")
    correct_html = f'<div class="correct-fact">→ Correct: {c["correct_fact"]}</div>' if c.get("correct_fact") else ""
    source_html = f'<div class="verdict-text" style="margin-top:0.3rem;font-size:0.78rem;color:#475569;">Source: {c["source"]}</div>' if c.get("source") and c["source"] != "N/A" else ""
    st.markdown(f"""
    <div class="claim-card">
      <span class="badge {badge_cls}">{icon} {verdict}</span>
      &nbsp;<span style="font-size:0.75rem;color:#475569;font-family:'JetBrains Mono',monospace;">{c.get('category','').upper()}</span>
      <div class="claim-text">"{c['claim']}"</div>
      <div class="verdict-text">{c.get('explanation','')}</div>
      {correct_html}{source_html}
    </div>
    """, unsafe_allow_html=True)


def render_summary(results):
    counts = {"Verified": 0, "Inaccurate": 0, "False": 0}
    for r in results:
        v = r.get("verdict", "False")
        counts[v] = counts.get(v, 0) + 1
    st.markdown(f"""
    <div class="summary-bar">
      <div><div class="stat-num" style="color:#6ee7b7">{counts['Verified']}</div><div class="stat-label">Verified</div></div>
      <div><div class="stat-num" style="color:#fbbf24">{counts['Inaccurate']}</div><div class="stat-label">Inaccurate</div></div>
      <div><div class="stat-num" style="color:#f87171">{counts['False']}</div><div class="stat-label">False</div></div>
      <div><div class="stat-num" style="color:#94a3b8">{len(results)}</div><div class="stat-label">Total</div></div>
    </div>
    """, unsafe_allow_html=True)


def main():
    st.markdown('<div class="hero-title">FactCheck Agent</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Upload any PDF and every factual claim gets checked against current data.</div>', unsafe_allow_html=True)

    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        st.error("Gemini API key not found. Add GEMINI_API_KEY in Streamlit secrets.")
        return

    uploaded = st.file_uploader("Drop a PDF here", type=["pdf"], label_visibility="collapsed")
    st.markdown('<div class="upload-hint">Works with marketing decks, reports, whitepapers — anything with stats.</div>', unsafe_allow_html=True)

    if uploaded and st.button("Run Fact-Check →"):
        with st.spinner("Reading PDF…"):
            text = extract_text_from_pdf(uploaded)

        if not text.strip():
            st.error("Couldn't extract text. Make sure the PDF is not a scanned image.")
            return

        st.markdown('<div class="step-label">STEP 1 — FINDING CLAIMS</div>', unsafe_allow_html=True)
        with st.spinner("Scanning for verifiable claims…"):
            try:
                claims = extract_claims(text, api_key)
            except Exception as e:
                st.error(f"Something went wrong during claim extraction: {e}")
                return

        st.success(f"Found **{len(claims)}** claims. Verifying each one…")
        st.markdown('<div class="step-label">STEP 2 — VERIFYING EACH CLAIM</div>', unsafe_allow_html=True)

        results = []
        progress = st.progress(0)
        cards = st.container()

        for i, claim in enumerate(claims):
            with st.spinner(f"Checking {i+1}/{len(claims)}: {claim['claim'][:60]}…"):
                try:
                    result = verify_claim(claim, api_key)
                except Exception as e:
                    result = {**claim, "verdict": "False", "confidence": "Low",
                              "explanation": f"Could not verify: {e}", "correct_fact": None, "source": "N/A"}
            results.append(result)
            with cards:
                render_claim_card(result)
            progress.progress((i + 1) / len(claims))
            time.sleep(0.2)

        progress.empty()
        st.markdown("---")
        st.markdown('<div class="step-label">SUMMARY</div>', unsafe_allow_html=True)
        render_summary(results)

        st.download_button(
            label="Download Full Report (JSON)",
            data=json.dumps(results, indent=2),
            file_name="factcheck_report.json",
            mime="application/json",
        )


if __name__ == "__main__":
    main()
