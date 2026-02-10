import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time
import requests
import re

st.set_page_config(page_title="Transcriptor Logopèdic", page_icon="🗣️")

# --- FUNCIONS AUXILIARS ---
def obtenir_url_descarrega_directa(url):
    if "drive.google.com" in url:
        match = re.search(r"/d/([^/]+)", url)
        if match:
            file_id = match.group(1)
            return f"https://docs.google.com/uc?export=download&id={file_id}"
    return url

# --- INICIALITZACIÓ DEL SESSION STATE ---
if "transcripcio_feta" not in st.session_state:
    st.session_state.transcripcio_feta = None
if "nom_fitxer" not in st.session_state:
    st.session_state.nom_fitxer = ""

# --- LÒGICA D'AUTENTICACIÓ ---
user_input = st.sidebar.text_input("Clau API o contrasenya d'accés", type="password")
api_key = None

if user_input:
    u_clean = user_input.strip()
    try:
        if "admin_password" in st.secrets and u_clean == st.secrets["admin_password"]:
            api_key = st.secrets["gemini_api_key_admin"]
            st.sidebar.success("✅ Accés concedit.")
        else:
            api_key = u_clean
    except Exception:
        api_key = u_clean

if not api_key:
    st.info("Introdueix la contrasenya o la teva API Key.")
    st.stop()

genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-2.5-flash") 

# --- SELECCIÓ DE FONT D'ENTRADA (AQUESTA ÉS L'ÚNICA INSTÀNCIA) ---
st.subheader("Configuració de la font")
opcio_font = st.radio(
    "Com vols carregar el fitxer?", 
    ["Pujar fitxer local", "Enllaç URL (Drive, Web)"],
    key="selector_font" # Afegim una clau única per seguretat
)

uploaded_file = None
url_input = ""
url_per_reproductor = None

if opcio_font == "Pujar fitxer local":
    uploaded_file = st.file_uploader(
        "Puja el fitxer de la sessió", 
        type=['mp4', 'mov', 'avi', 'mp3', 'wav', 'm4a']
    )
    if uploaded_file:
        url_per_reproductor = uploaded_file
        # Lògica per netejar la memòria si canviem de fitxer
        if uploaded_file.name != st.session_state.nom_fitxer:
            st.session_state.transcripcio_feta = None
            st.session_state.nom_fitxer = uploaded_file.name
else:
    url_input = st.text_input("Enganxa la URL del vídeo o àudio:")
    if url_input:
        url_per_reproductor = obtenir_url_descarrega_directa(url_input)
        st.info("Nota: Si és un enllaç de Drive, assegura't que sigui públic.")
        if url_input != st.session_state.nom_fitxer:
            st.session_state.transcripcio_feta = None
            st.session_state.nom_fitxer = url_input

# --- VISOR DE MITJANS (PREVISUALITZACIÓ) ---
if url_per_reproductor:
    st.markdown("### Previsualització")
    es_audio = False
    if opcio_font == "Pujar fitxer local":
        es_audio = uploaded_file.type.startswith('audio')
    else:
        es_audio = any(ext in url_input.lower() for ext in ['.mp3', '.wav', '.m4a'])

    if es_audio:
        st.audio(url_per_reproductor)
    else:
        st.video(url_per_reproductor)

# --- BOTÓ DE PROCESSAMENT ---
if st.button("🚀 Generar Transcripció"):
    tmp_path = None
    try:
        with st.spinner("Preparant i analitzant el fitxer..."):
            
            # Procés de descàrrega/preparació segons la font
            if opcio_font == "Pujar fitxer local" and uploaded_file:
                extensio = os.path.splitext(uploaded_file.name)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=extensio) as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
            
            elif opcio_font == "Enllaç URL (Drive, Web)" and url_input:
                url_directa = obtenir_url_descarrega_directa(url_input)
                extensio = ".mp4" if "video" in url_input.lower() else ".mp3"
                
                resposta = requests.get(url_directa, stream=True)
                if resposta.status_code == 200:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=extensio) as tmp:
                        for chunk in resposta.iter_content(chunk_size=8192):
                            tmp.write(chunk)
                        tmp_path = tmp.name
                else:
                    st.error("No s'ha pogut descarregar el fitxer. Revisa els permisos.")
                    st.stop()
            
            # Puja a Gemini i processa
            if tmp_path:
                video_gemini = genai.upload_file(path=tmp_path)
                
                progress_bar = st.progress(0)
                while video_gemini.state.name == "PROCESSING":
                    time.sleep(2)
                    video_gemini = genai.get_file(video_gemini.name)
                    progress_bar.progress(50)
                
                progress_bar.progress(100)
                
                instruccions = """
        Actua com un transcriptor especialitzat en logopèdia i lingüística clínica.
        La teva tasca és realitzar una transcripció literal i fidel d'aquest vídeo d'alumnes amb dificultats de llenguatge.

        INSTRUCCIONS CRÍTIQUES:
        1. LLIURAMENT LITERAL: Transcriu exactament el que se sent. No corregeixis la gramàtica ni la pronúncia.
        2. NO NORMALITZIS: Si l'alumne diu una paraula malament, escriu exactament el que diu.
        3. FORMAT: Utilitza el format "Parlant X: [Text]". Identifica examinador i alumne.
        4. RESTRICCIÓ: No afegeixis comentaris personals.

        Després de la transcripció, llista les 4 millors produccions (més llargues o complexes) de l'alumne.
        """
                
                res = model.generate_content([instruccions, video_gemini])
                st.session_state.transcripcio_feta = res.text
                
                os.remove(tmp_path)
                video_gemini.delete()
                st.success("Transcripció completada!")
            else:
                st.warning("No s'ha trobat cap fitxer per processar.")

    except Exception as e:
        st.error(f"S'ha produït un error: {e}")

# --- MOSTRAR RESULTAT ---
if st.session_state.transcripcio_feta:
    st.markdown("---")
    st.subheader("Resultat de la transcripció")
    
    # Vinculem el text_area directament a la clau del session_state.
    # Això fa que qualsevol edició actualitzi automàticament st.session_state.transcripcio_feta
    st.text_area(
        "Pots editar el text directament aquí:", 
        key="transcripcio_feta", 
        height=400
    )
    
    # Ara el botó de descàrrega sempre tindrà la versió actualitzada (l'editada)
    st.download_button(
        label="Baixar transcripció (.txt)", 
        data=st.session_state.transcripcio_feta, 
        file_name="transcripcio_logopedia.txt"
    )
