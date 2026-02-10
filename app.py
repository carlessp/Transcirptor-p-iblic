import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time

st.set_page_config(page_title="Transcriptor Logopèdic", page_icon="🗣️")

st.title("🗣️ Transcriptor Logopèdic IA")

# --- LÒGICA D'AUTENTICACIÓ ---
# Un sol camp per a tot: clau personal o contrasenya de grup
user_input = st.sidebar.text_input("Clau API o Contrasenya d'accés", type="password")

api_key = None

if user_input:
    # Comprovem si l'usuari ha posat la "contrasenya màgica"
    # Aquests valors han d'estar definits als Secrets de Streamlit
    if "admin_password" in st.secrets and user_input == st.secrets["admin_password"]:
        api_key = st.secrets["gemini_api_key_admin"]
        st.sidebar.success("✅ Accés concedit amb la clau del centre.")
    else:
        # Si no és la contrasenya, assumim que és la seva pròpia API Key
        api_key = user_input
        st.sidebar.info("ℹ️ Fent servir la clau API personal.")

# Aturem l'execució si no tenim cap clau vàlida
if not api_key:
    st.info("Introdueix la contrasenya del centre o la teva pròpia Gemini API Key per començar.")
    st.stop()

# Configuració del model (he posat 2.0-flash que és l'estàndard actual)
try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash") 
except Exception as e:
    st.error(f"Error de configuració: {e}")
    st.stop()

# --- RECTA DEL CODI (PUJADA I TRANSCRIPCIÓ) ---
uploaded_file = st.file_uploader("Puja el vídeo (mp4, mov, avi)", type=['mp4', 'mov', 'avi'])

if uploaded_file and st.button("Generar Transcripció"):
    try:
        with st.spinner("Processant..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name

            video_gemini = genai.upload_file(path=tmp_path)

            progress_bar = st.progress(0)
            while video_gemini.state.name == "PROCESSING":
                time.sleep(2)
                video_gemini = genai.get_file(video_gemini.name)
                progress_bar.progress(50)
            
            progress_bar.progress(100)
            
            instruccions = """
            Actua com un transcriptor especialitzat en logopèdia. 
            Realitza una transcripció literal (verbatim) sense corregir errors.
            Format: "Parlant X: [Text]".
            Llista les 4 produccions més complexes al final.
            """
            
            res = model.generate_content([instruccions, video_gemini])

            st.success("Fet!")
            st.text_area("Resultat:", res.text, height=400)
            
            st.download_button("Baixar fitxer .txt", res.text, file_name="transcripcio.txt")

            os.remove(tmp_path)
            video_gemini.delete()

    except Exception as e:
        st.error(f"S'ha produït un error: {e}")
