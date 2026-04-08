import streamlit as st
import requests
import re
import json
import urllib.parse

st.set_page_config(page_title="Glasses Rim Classifier", layout="wide")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_images(query, num=4):
    """Fetch image URLs from Bing Images."""
    try:
        resp = requests.get(
            'https://www.bing.com/images/search',
            params={'q': query, 'form': 'HDRSC2', 'first': '1'},
            headers=HEADERS,
            timeout=8,
        )
        resp.raise_for_status()
        urls = re.findall(r'murl&quot;:&quot;(https?://[^&]+?)&quot;', resp.text)
        seen = set()
        unique = []
        for u in urls:
            if u not in seen:
                seen.add(u)
                unique.append(u)
        return unique[:num]
    except Exception:
        return []


def load_models():
    """Load models from session or file."""
    if 'models' not in st.session_state:
        try:
            with open('glasses_models.json', 'r') as f:
                st.session_state.models = json.load(f)
        except FileNotFoundError:
            st.session_state.models = []
    return st.session_state.models


def init_state():
    if 'classifications' not in st.session_state:
        st.session_state.classifications = {}
    if 'current_index' not in st.session_state:
        st.session_state.current_index = 0


def classify(rim_type):
    models = st.session_state.models
    idx = st.session_state.current_index
    if idx < len(models):
        st.session_state.classifications[models[idx]] = rim_type
        st.session_state.current_index = min(idx + 1, len(models) - 1)


def go_to(idx):
    models = st.session_state.models
    st.session_state.current_index = max(0, min(idx, len(models) - 1))


def next_unclassified():
    models = st.session_state.models
    cls = st.session_state.classifications
    start = st.session_state.current_index + 1
    for i in range(start, len(models)):
        if models[i] not in cls:
            st.session_state.current_index = i
            return
    for i in range(0, start):
        if models[i] not in cls:
            st.session_state.current_index = i
            return


def undo():
    if st.session_state.current_index > 0:
        st.session_state.current_index -= 1
        model = st.session_state.models[st.session_state.current_index]
        st.session_state.classifications.pop(model, None)


# --- INIT ---
load_models()
init_state()
models = st.session_state.models

if not models:
    st.title("Glasses Rim Classifier")
    st.warning("No models loaded. Upload glasses_models.json below.")
    uploaded = st.file_uploader("Upload glasses_models.json", type="json")
    if uploaded:
        st.session_state.models = json.load(uploaded)
        st.rerun()
    st.stop()

idx = st.session_state.current_index
classifications = st.session_state.classifications
current_model = models[idx]

# Count stats
full_count = sum(1 for v in classifications.values() if v == 'Full Rim')
half_count = sum(1 for v in classifications.values() if v == 'Half Rim')
rimless_count = sum(1 for v in classifications.values() if v == 'Rimless')
total_done = full_count + half_count + rimless_count
pct = (total_done / len(models) * 100) if models else 0

# --- TOP BAR ---
tcol1, tcol2, tcol3 = st.columns([2, 3, 2])
with tcol1:
    st.markdown(f"**#{idx + 1}** / {len(models)}")
with tcol2:
    st.progress(pct / 100, text=f"{total_done} classified ({pct:.1f}%)")
with tcol3:
    st.markdown(f"🟢 {full_count} &nbsp; 🟠 {half_count} &nbsp; 🔵 {rimless_count} &nbsp; ⚪ {len(models) - total_done}")

# --- MAIN LAYOUT ---
left, right = st.columns([1, 3])

with left:
    # Model name
    existing = classifications.get(current_model)
    if existing:
        color = '#2d6a4f' if existing == 'Full Rim' else '#e76f51' if existing == 'Half Rim' else '#457b9d'
        st.markdown(f'<div style="background:#16213e;border:2px solid {color};border-radius:8px;padding:12px;text-align:center;font-size:18px;font-weight:bold;color:white;margin-bottom:8px;">{current_model}<br><span style="font-size:12px;color:{color};">{existing}</span></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="background:#16213e;border:2px solid #0f3460;border-radius:8px;padding:12px;text-align:center;font-size:18px;font-weight:bold;color:white;margin-bottom:8px;">{current_model}</div>', unsafe_allow_html=True)

    # Classify buttons
    c1, c2, c3 = st.columns(3)
    with c1:
        st.button("1️⃣ Full Rim", on_click=classify, args=('Full Rim',), use_container_width=True, type="primary")
    with c2:
        st.button("2️⃣ Half Rim", on_click=classify, args=('Half Rim',), use_container_width=True)
    with c3:
        st.button("3️⃣ Rimless", on_click=classify, args=('Rimless',), use_container_width=True)

    # Navigation
    st.markdown("---")
    n1, n2, n3, n4 = st.columns(4)
    with n1:
        st.button("⬅️", on_click=go_to, args=(idx - 1,), use_container_width=True)
    with n2:
        st.button("➡️", on_click=go_to, args=(idx + 1,), use_container_width=True)
    with n3:
        st.button("Undo", on_click=undo, use_container_width=True)
    with n4:
        st.button("Next empty", on_click=next_unclassified, use_container_width=True)

    # Jump to
    jump = st.number_input("Go to #", min_value=1, max_value=len(models), value=idx + 1, step=1)
    if jump != idx + 1:
        go_to(jump - 1)
        st.rerun()

    # Export / Import
    st.markdown("---")
    # Export CSV
    csv_data = "Model,Rim Type\n"
    for m, r in classifications.items():
        csv_data += f'"{m}","{r}"\n'
    st.download_button("📥 Export CSV", csv_data, "glasses_classifications.csv", "text/csv", use_container_width=True)

    # Import CSV
    uploaded_csv = st.file_uploader("Import CSV", type="csv", label_visibility="collapsed")
    if uploaded_csv:
        content = uploaded_csv.read().decode('utf-8')
        imported = 0
        for line in content.split('\n')[1:]:
            line = line.strip()
            m = re.match(r'^"(.+?)","(.+?)"$', line)
            if m and m.group(2) in ('Full Rim', 'Half Rim', 'Rimless'):
                st.session_state.classifications[m.group(1)] = m.group(2)
                imported += 1
        st.success(f"Imported {imported} classifications!")
        st.rerun()

# --- RIGHT: IMAGES ---
with right:
    with st.spinner("Loading images..."):
        image_urls = fetch_images(current_model + ' glasses')

    if image_urls:
        # Display images in a grid
        cols = st.columns(4)
        for i, url in enumerate(image_urls):
            with cols[i % 4]:
                st.image(url, use_container_width=True)
    else:
        st.info(f"No images found for '{current_model}'. Try Google: [Search]({urllib.parse.quote(current_model + ' glasses')})")


# --- KEYBOARD SHORTCUTS via JS ---
st.markdown("""
<script>
document.addEventListener('keydown', function(e) {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

    const buttons = document.querySelectorAll('button');
    if (e.key === '1') {
        for (const b of buttons) { if (b.textContent.includes('Full Rim')) { b.click(); break; } }
    } else if (e.key === '2') {
        for (const b of buttons) { if (b.textContent.includes('Half Rim')) { b.click(); break; } }
    } else if (e.key === '3') {
        for (const b of buttons) { if (b.textContent.includes('Rimless')) { b.click(); break; } }
    } else if (e.key === 'u' || e.key === 'U') {
        for (const b of buttons) { if (b.textContent.includes('Undo')) { b.click(); break; } }
    } else if (e.key === 'n' || e.key === 'N') {
        for (const b of buttons) { if (b.textContent.includes('Next empty')) { b.click(); break; } }
    }
});
</script>
""", unsafe_allow_html=True)
