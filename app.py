import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time

# Configuració de la pàgina
st.set_page_config(page_title="Transcriptor Logopèdic", page_icon="🗣️")

st.title("🗣️ Transcriptor Logopèdic IA")
st.markdown("""
Aquesta eina realitza transcripcions literals per a l'anàlisi lingüística clínica.
""")

# 1. Configuració de la API Key (Seguretat)
# En producció, farem servir st.secrets, però per provar ho podem demanar a l'usuari
api_key = st.sidebar.text_input("Gemini API Key", type="password")

if not api_key:
    st.info("Si us plau, introdueix la teva API Key de Gemini a la barra lateral per començar.", icon="🔑")
else:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    # 2. Pujada del fitxer
    uploaded_file = st.file_uploader("Puja el vídeo de l'alumne (mp4, mov, avi)", type=['mp4', 'mov', 'avi'])

    if uploaded_file is not None:
        if st.button("Generar Transcripció"):
            try:
                with st.spinner("Preparant fitxer i connectant amb Gemini..."):
                    # Crear un fitxer temporal per desar el vídeo pujat
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name

                    # Pujar a Gemini
                    video_gemini = genai.upload_file(path=tmp_path)

                    # Esperar processament
                    progress_bar = st.progress(0)
                    while video_gemini.state.name == "PROCESSING":
                        time.sleep(2)
                        video_gemini = genai.get_file(video_gemini.name)
                        progress_bar.progress(50)
                    
                    progress_bar.progress(100)
                    st.info("🧠 Analitzant i transcrivint...")

                    # Instruccions (les teves originals)
                    instruccions = """
                    Actua com un transcriptor especialitzat en logopèdia i lingüística clínica.
                    La teva tasca és realitzar una transcripció literal i fidel d'aquest vídeo.
                    1. LLIURAMENT LITERAL: No corregeixis la gramàtica ni la pronúncia.
                    2. NO NORMALITZIS: Escriu exactament el que es diu.
                    3. FORMAT: "Parlant X: [Text]". Identifica examinador i alumne.
                    4. RESTRICCIÓ: No afegeixis comentaris personals.
                    Després, llista les 4 millors produccions (més llargues o complexes) de l'alumne.
                    """

                    res = model.generate_content([instruccions, video_gemini])

                    # 3. Resultats
                    st.success("Transcripció completada!")
                    st.text_area("Resultat:", res.text, height=400)

                    # Botó de descàrrega
                    st.download_button(
                        label="Descarregar Transcripció (.txt)",
                        data=res.text,
                        file_name="transcripcio_logopedia.txt",
                        mime="text/plain"
                    )

                    # Neteja
                    os.remove(tmp_path)
                    video_gemini.delete()

            except Exception as e:
                st.error(f"S'ha produït un error: {e}")
