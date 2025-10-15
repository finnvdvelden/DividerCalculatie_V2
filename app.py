# app.py (secure version)
import streamlit as st
import pandas as pd
import io
import gc
from processing import process_df

st.set_page_config(page_title="Divider Calculatie", layout="wide")

# --- LOGIN (formulier-variant) ---
PASSWORD = st.secrets.get("APP_PASSWORD", None)

if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    with st.form("login_form"):
        st.markdown("**Log in om de app te gebruiken**")
        pw = st.text_input("Voer app-wachtwoord in", type="password")
        submitted = st.form_submit_button("Login")
    if submitted:
        if PASSWORD is None:
            st.error("App wachtwoord is nog niet ingesteld. Beheerder moet st.secrets invullen.")
        elif pw == PASSWORD:
            st.session_state.auth = True
            st.success("Ingelogd — u kunt nu verder")
        else:
            st.error("Verkeerd wachtwoord")
    if not st.session_state.auth:
        st.stop()
# ----------------------------------------------------

st.title("Divider Calculatie - upload Excel en download resultaat")
st.markdown("Upload je Excel bestand. Verwachte kolommen: Stuklijst, Soort, Omschrijving, P1..P5, Netto lengte PL")

# Divider editor with defaults
default = [
    {"name":"2×2","L":166,"B":117,"H":52},
    {"name":"2×4","L":166,"B":57,"H":52},
    {"name":"3×2","L":111,"B":113,"H":52},
    {"name":"3×4","L":111,"B":57,"H":52},
    {"name":"4×2","L":82,"B":115,"H":52},
    {"name":"4×4","L":82,"B":57,"H":52},
    {"name":"4×8","L":82,"B":28,"H":52},
    {"name":"6×4","L":52,"B":56,"H":30},
]
st.markdown("Wijzig dividerwaarden als dat nodig is")
div_df = st.data_editor(pd.DataFrame(default), num_rows="dynamic", use_container_width=True, key="div_editor")

height_override = st.number_input("Hoogte override voor 95mm check (0 = geen)", min_value=0, value=0)
height_override_val = None if height_override == 0 else int(height_override)

uploaded = st.file_uploader("Excel (xlsx)", type=["xlsx", "xls"])

# Veiligheidschecks voor uploads
MAX_BYTES = 20 * 1024 * 1024  # 20 MB, wijzig naar wens

if uploaded is not None:
    size = uploaded.getbuffer().nbytes
    if size > MAX_BYTES:
        st.error(f"Bestand te groot ({round(size/1024/1024,2)} MB). Maximaal {MAX_BYTES/(1024*1024)} MB toegestaan.")
        st.stop()
    try:
        df_in = pd.read_excel(uploaded)
    except Exception as e:
        st.error("Kon het Excel bestand niet lezen: " + str(e))
        st.stop()

    # Kolomvalidatie
    required = ["Stuklijst","Soort","Omschrijving","P1","P2","P3","P4","P5","Netto lengte PL"]
    missing = [c for c in required if c not in df_in.columns]
    if missing:
        st.error(f"Ontbrekende kolommen: {missing}. Pas je Excel aan of pas de kolomnamen in processing.py.")
        st.stop()

    st.markdown("Voorbeeld van je bestand")
    st.dataframe(df_in.head(), use_container_width=True)

    if st.button("Run analysis"):
        with st.spinner("Verwerken..."):
            out_df = process_df(df_in, dividers_rows=div_df.to_dict(orient="records"), height_override_for_95=height_override_val)
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                out_df.to_excel(writer, index=False, sheet_name="Indeling")
            buf.seek(0)
            st.success("Klaar, download hieronder")
            st.download_button("Download indeling_resultaat.xlsx", data=buf, file_name="indeling_resultaat.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            st.dataframe(out_df.head(), use_container_width=True)
            # Opruimen
            try:
                del buf
                gc.collect()
            except:
                pass
