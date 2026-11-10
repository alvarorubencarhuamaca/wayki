"""Wayki – tu amigo para los trámites de la Municipalidad de Huayucachi.

Ejecutar:  streamlit run app.py
"""
import os

import streamlit as st

from wayki.core import BuscadorTUPA, ficha_sin_ia, responder, transcribir

st.set_page_config(page_title="Wayki · Trámites Huayucachi", page_icon="🏛️", layout="centered")


def get_key() -> str:
    try:
        return st.secrets.get("GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
    except Exception:  # sin secrets.toml
        return os.getenv("GROQ_API_KEY", "")


@st.cache_resource
def cargar():
    return BuscadorTUPA()


buscador = cargar()
API_KEY = get_key()

st.title("🏛️ Wayki")
st.markdown(
    "**Pregunta como le preguntarías a un vecino.** Wayki lee el TUPA oficial de la "
    "Municipalidad Distrital de Huayucachi (404 páginas escaneadas) y te dice "
    "**qué llevar, cuánto cuesta, cuánto demora y a dónde ir**, citando la página."
)

with st.sidebar:
    st.subheader("Sobre los datos")
    m = buscador.meta
    st.write(f"**Fuente:** {m['fuente']}")
    st.write(f"**Norma:** {m['norma']}")
    st.write(f"**Procedimientos indexados:** {len(buscador.procs)}")
    st.markdown(f"[PDF original]({m['url']})")
    st.divider()
    st.write("🟢 IA activa (Groq)" if API_KEY else "🟡 Modo sin IA: ficha directa del TUPA")
    mostrar_debug = st.toggle("Ver fragmentos recuperados", value=False)
    st.caption("Wayki orienta; no reemplaza la atención oficial. Verifica montos en caja.")

EJEMPLOS = [
    "Quiero abrir una bodega en mi casa, ¿qué necesito?",
    "¿Cuánto cuesta el certificado de defensa civil para un local pequeño?",
    "¿Cómo pido información pública a la municipalidad?",
    "Voy a cerrar mi negocio, ¿qué trámite hago?",
]

if "pregunta" not in st.session_state:
    st.session_state.pregunta = ""

tab_txt, tab_voz = st.tabs(["✍️ Escribir", "🎙️ Hablar"])
with tab_txt:
    cols = st.columns(2)
    for i, ej in enumerate(EJEMPLOS):
        if cols[i % 2].button(ej, key=f"ej{i}", use_container_width=True):
            st.session_state.pregunta = ej
    texto = st.text_input("Tu pregunta", value=st.session_state.pregunta,
                          placeholder="Ej.: quiero poner un restaurante, ¿qué licencia saco?")
    if texto:
        st.session_state.pregunta = texto
with tab_voz:
    if not API_KEY:
        st.info("La voz necesita la API key de Groq (Whisper). Escribe tu pregunta mientras tanto.")
    else:
        audio = st.audio_input("Graba tu pregunta (en español)")
        if audio is not None:
            with st.spinner("Escuchando con Whisper…"):
                try:
                    st.session_state.pregunta = transcribir(audio.getvalue(), API_KEY)
                    st.success(f"Entendí: “{st.session_state.pregunta}”")
                except Exception as e:  # red o cuota
                    st.error(f"No pude transcribir el audio: {e}")

pregunta = st.session_state.pregunta.strip()
if pregunta:
    resultados = buscador.buscar(pregunta, k=4)
    if not resultados:
        st.warning(
            "No encontré ese trámite en el TUPA que tengo indexado. Por ahora conozco los "
            f"{len(buscador.procs)} procedimientos del TUPA 2023 (licencias de funcionamiento, "
            "defensa civil/ITSE, espectáculos y acceso a la información). "
            "Para otros trámites, acércate a la Unidad de Trámite Documentario."
        )
        st.stop()

    if API_KEY:
        with st.spinner("Leyendo el TUPA por ti…"):
            try:
                ans = responder(pregunta, resultados, API_KEY)
            except Exception as e:
                st.warning(f"La IA no respondió ({e}). Te muestro la ficha directa del TUPA.")
                ans = ficha_sin_ia(resultados[0])
    else:
        ans = ficha_sin_ia(resultados[0])

    if not ans.get("encontrado", True):
        st.warning(ans.get("resumen") or "No encontré ese trámite en el TUPA.")
    else:
        st.subheader(ans.get("procedimiento", ""))
        if ans.get("codigo"):
            st.caption(f"Código TUPA: {ans['codigo']} · Páginas del PDF: {ans.get('pagina_tupa', '')}")
        st.write(ans.get("resumen", ""))
        c1, c2 = st.columns(2)
        c1.metric("💰 Costo", ans.get("costo", "—"))
        c2.metric("⏱️ Plazo", ans.get("plazo", "—"))
        st.markdown("**📋 Lleva esto:**")
        for i, req in enumerate(ans.get("requisitos", []), 1):
            st.checkbox(req, key=f"req{i}")
        st.markdown(f"**📍 Dónde:** {ans.get('donde', '')}")
        if ans.get("consejo"):
            st.info(f"💡 {ans['consejo']}")

    with st.expander("Otros trámites parecidos"):
        for r in resultados[1:]:
            st.write(f"• {r.proc['nombre']} (pág. {r.proc['paginas']})")

    if mostrar_debug:
        st.divider()
        st.caption("Fragmentos recuperados (TF-IDF) que vio el modelo")
        for r in resultados:
            with st.expander(f"{r.score:.2f} · {r.proc['nombre'][:80]}"):
                st.text(r.proc["texto"][:3000])
        if "_tokens" in ans:
            st.json(ans["_tokens"])
