"""Wayki – el TUPA de tu municipalidad, explicado como un vecino.

Prueba piloto: 8 municipalidades de la provincia de Huancayo (ver data/municipios.json).
Ejecutar:  streamlit run app.py
"""
import csv
import datetime as dt
import html
import os
import urllib.parse
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from wayki.core import BuscadorTUPA, ficha_sin_ia, listar_municipios, responder, transcribir

st.set_page_config(page_title="Wayki · Tu trámite a la primera", page_icon="🏛️",
                   layout="centered", initial_sidebar_state="collapsed")

# ---------------------------------------------------------------- estilos
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{--rojo:#B83227;--rojo-osc:#8E241C;--crema:#FBF7F2;--arena:#F3ECE3;--carbon:#2B2B2B;--gris:#6B6B6B;--verde:#2E7D4F;}
html, body, [class*="css"], .stMarkdown, .stButton button, input, textarea {font-family:'Inter',system-ui,sans-serif !important;}
.block-container{padding-top:1.2rem;max-width:760px;}
#MainMenu, footer, header [data-testid="stToolbar"]{visibility:hidden;}

.hero{background:linear-gradient(135deg,var(--rojo) 0%,var(--rojo-osc) 100%);color:#fff;border-radius:22px;
      padding:26px 26px 22px;margin-bottom:14px;box-shadow:0 10px 30px rgba(184,50,39,.25);}
.hero .marca{font-size:15px;font-weight:700;letter-spacing:.08em;opacity:.9;text-transform:uppercase}
.hero h1{color:#fff;font-size:30px;line-height:1.15;font-weight:800;margin:6px 0 8px;padding:0}
.hero p{font-size:16px;opacity:.95;margin:0}
.hero .stats{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px}
.hero{position:relative;overflow:hidden;padding-bottom:40px}
.hero::after{content:"";position:absolute;left:0;right:0;bottom:0;height:18px;opacity:.55;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='36' height='18' viewBox='0 0 36 18'%3E%3Cpath d='M0 18 L9 9 L18 18 Z' fill='%23F3ECE3'/%3E%3Cpath d='M18 18 L27 9 L36 18 Z' fill='%23E8A33D'/%3E%3Cpath d='M9 9 L18 0 L27 9 L18 18 Z' fill='none' stroke='%23F3ECE3' stroke-width='2'/%3E%3Crect x='16' y='7' width='4' height='4' fill='%23E8A33D'/%3E%3C/svg%3E");
  background-repeat:repeat-x;background-size:36px 18px}
.acciones{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 4px}
.acciones a{flex:1 1 150px;text-align:center;text-decoration:none !important;border-radius:14px;padding:12px 10px;
  font-weight:700;font-size:15px;border:1px solid #E6DCCF;background:#fff;color:var(--carbon) !important}
.acciones a.wa{background:#1FAF5A;border-color:#1FAF5A;color:#fff !important}
.acciones a:hover{transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,0,0,.08)}
.hero .stat{background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.25);border-radius:999px;
            padding:6px 12px;font-size:13px;font-weight:600}

.etiqueta{font-size:13px;font-weight:700;color:var(--gris);text-transform:uppercase;letter-spacing:.06em;margin:14px 0 6px}

.stButton button{border-radius:14px;border:1px solid #E6DCCF;background:#fff;color:var(--carbon);
                 font-weight:600;min-height:52px;font-size:15px;transition:all .15s}
.stButton button:hover{border-color:var(--rojo);color:var(--rojo);transform:translateY(-1px);
                       box-shadow:0 4px 12px rgba(0,0,0,.06)}
.stButton button[kind="primary"]{background:var(--rojo);color:#fff;border:none}
.stButton button[kind="primary"]:hover{background:var(--rojo-osc);color:#fff}
.stTextInput input{border-radius:14px;min-height:52px;font-size:16px;border:1.5px solid #E6DCCF;background:#fff}
.stTextInput input:focus{border-color:var(--rojo);box-shadow:0 0 0 3px rgba(184,50,39,.12)}

.resp-titulo{font-size:22px;font-weight:800;color:var(--carbon);margin:18px 0 4px;line-height:1.25}
.resp-resumen{font-size:16px;color:#444;margin-bottom:12px}
.fichas{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:8px 0 6px}
.ficha{background:#fff;border:1px solid #EFE6DA;border-radius:16px;padding:14px 14px 12px;box-shadow:0 2px 8px rgba(0,0,0,.04)}
.ficha .ico{font-size:22px}
.ficha .lab{font-size:12px;font-weight:700;color:var(--gris);text-transform:uppercase;letter-spacing:.05em;margin-top:4px}
.ficha .val{font-size:18px;font-weight:800;color:var(--carbon);margin-top:2px;line-height:1.25;word-wrap:break-word}
.ficha.donde .val{font-size:14px;font-weight:600}
@media (max-width:640px){.fichas{grid-template-columns:1fr;gap:8px}.hero h1{font-size:25px}
  .ficha{display:grid;grid-template-columns:34px 1fr;column-gap:10px;align-items:center;padding:10px 14px}
  .ficha .ico{grid-row:span 2}.ficha .lab{margin-top:0}}

.consejo{background:#FFF7E6;border-left:5px solid #E8A33D;border-radius:12px;padding:12px 14px;margin:12px 0;font-size:15px}
.fuente{display:flex;align-items:center;gap:10px;background:#EEF7F1;border:1px solid #CFE6D7;color:#1F5A37;
        border-radius:14px;padding:12px 14px;margin:12px 0;font-size:14px}
.fuente a{color:#1F5A37;font-weight:700}
.aviso{background:#FFF1F0;border:1px solid #F3C9C5;border-radius:14px;padding:14px;color:#7A1F17;font-size:15px}

.pasos{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:8px}
.paso{background:var(--arena);border-radius:14px;padding:12px;font-size:14px;color:#444}
.paso b{display:block;color:var(--rojo);font-size:13px;text-transform:uppercase;letter-spacing:.05em;margin-bottom:2px}
@media (max-width:640px){.pasos{grid-template-columns:1fr}}
.pie{font-size:12px;color:var(--gris);text-align:center;margin-top:28px}
</style>
""", unsafe_allow_html=True)

e = html.escape  # todo texto del TUPA o del LLM pasa por aquí antes de ir al HTML
APP_URL = "https://qthbrgdhnhjyhp7pywtvgz.streamlit.app/"
FEEDBACK = Path(__file__).parent / "feedback_log.csv"  # efímero en Streamlit Cloud (se borra al reiniciar)

_c1, _c2 = st.columns([3, 1])
if _c2.toggle("🔠 Letra grande", key="letra_grande"):
    st.markdown("<style>.block-container{zoom:1.18}</style>", unsafe_allow_html=True)


def boton_escuchar(texto: str):
    """Lee la respuesta en voz alta con la voz del navegador (Web Speech API, gratis)."""
    t = texto.replace("\\", " ").replace("`", " ").replace("$", "S/ ").replace("\n", " ").replace("</", " ")
    components.html(f"""
    <button id="b" style="width:100%;padding:12px;border-radius:14px;border:1px solid #E6DCCF;background:#fff;
      font:700 15px Inter,system-ui,sans-serif;color:#2B2B2B;cursor:pointer">🔊 Escuchar respuesta</button>
    <script>
      const txt = `{t}`; const b = document.getElementById('b'); let hablando = false;
      b.onclick = () => {{
        const s = window.speechSynthesis;
        if (hablando) {{ s.cancel(); hablando = false; b.textContent = '🔊 Escuchar respuesta'; return; }}
        const u = new SpeechSynthesisUtterance(txt); u.lang = 'es-PE'; u.rate = 0.95;
        const v = s.getVoices().find(x => x.lang.startsWith('es')); if (v) u.voice = v;
        u.onend = () => {{ hablando = false; b.textContent = '🔊 Escuchar respuesta'; }};
        s.cancel(); s.speak(u); hablando = true; b.textContent = '⏹️ Detener';
      }};
    </script>""", height=56)


def guardar_feedback(slug: str, pregunta: str, procedimiento: str, util: bool):
    try:
        nuevo = not FEEDBACK.exists()
        with FEEDBACK.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if nuevo:
                w.writerow(["fecha", "municipalidad", "pregunta", "procedimiento", "util"])
            w.writerow([dt.datetime.now().isoformat(timespec="seconds"), slug, pregunta, procedimiento, int(util)])
    except OSError:
        pass


def resumen_feedback(slug: str):
    try:
        with FEEDBACK.open(encoding="utf-8") as f:
            filas = [r for r in csv.DictReader(f) if r["municipalidad"] == slug]
    except OSError:
        return None
    if not filas:
        return None
    return len(filas), sum(int(r["util"]) for r in filas)


# ---------------------------------------------------------------- datos y claves
def get_key() -> str:
    try:
        key = st.secrets.get("GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
    except Exception:  # sin secrets.toml
        key = os.getenv("GROQ_API_KEY", "")
    return key if key.startswith("gsk_") else ""  # ignora el texto de ejemplo


@st.cache_resource
def cargar(slug: str):
    return BuscadorTUPA(slug)


@st.cache_data(show_spinner=False, ttl=3600)
def respuesta_ia(pregunta: str, slug: str, _resultados, municipio: str):
    """Cachea la respuesta: marcar el checklist no vuelve a llamar al LLM."""
    return responder(pregunta, _resultados, API_KEY, municipio)


MUNIS = listar_municipios()
API_KEY = get_key()
TOTAL = sum(len(cargar(s).procs) for s in MUNIS)

if "pregunta" not in st.session_state:
    st.session_state.pregunta = ""

# ---------------------------------------------------------------- portada
st.markdown(f"""
<div class="hero">
  <div class="marca">🏛️ Wayki</div>
  <h1>Tu trámite municipal,<br>a la primera.</h1>
  <p>El TUPA de tu municipalidad tiene cientos de páginas. Pregúntale a Wayki como le preguntarías
     a un vecino: te dice <b>qué llevar, cuánto pagar, cuánto demora y a dónde ir</b>.</p>
  <div class="stats">
    <span class="stat">📍 {len(MUNIS)} municipalidades</span>
    <span class="stat">📑 {TOTAL} procedimientos</span>
    <span class="stat">✔ Respuestas con página del TUPA oficial</span>
  </div>
</div>
""", unsafe_allow_html=True)

slug = st.selectbox("📍 Tu municipalidad", list(MUNIS), format_func=lambda s: MUNIS[s])
buscador = cargar(slug)
m = buscador.meta
if m.get("extraccion", "").startswith("OCR"):
    st.caption("🟡 El TUPA de esta municipalidad es un PDF escaneado: Wayki lo lee con OCR y puede haber "
               "errores de lectura. Verifica los montos en la página citada.")

# ---------------------------------------------------------------- pregunta
EJEMPLOS = [
    ("🏪", "Abrir mi bodega", "Quiero abrir una bodega en mi casa, ¿qué necesito?"),
    ("🔥", "Defensa Civil", "¿Cuánto cuesta el certificado de Defensa Civil para un local pequeño?"),
    ("💍", "Casarme", "Quiero casarme, ¿qué necesito?"),
    ("🔒", "Cerrar mi negocio", "Voy a cerrar mi negocio, ¿qué trámite hago?"),
    ("📄", "Pedir información", "¿Cómo pido información pública a la municipalidad?"),
    ("🔁", "Traspasar negocio", "Quiero traspasar mi negocio a otra persona, ¿qué hago?"),
]

st.markdown('<div class="etiqueta">¿Qué trámite necesitas?</div>', unsafe_allow_html=True)
cols = st.columns(3)
for i, (ico, corto, larga) in enumerate(EJEMPLOS):
    if cols[i % 3].button(f"{ico}  {corto}", key=f"ej{i}", use_container_width=True):
        st.session_state.pregunta = larga

tab_txt, tab_voz = st.tabs(["✍️ Escribir", "🎙️ Hablar"])
with tab_txt:
    with st.form("form_pregunta", clear_on_submit=False, border=False):
        c1, c2 = st.columns([4, 1])
        texto = c1.text_input("Tu pregunta", value=st.session_state.pregunta, label_visibility="collapsed",
                              placeholder="Ej.: quiero poner un restaurante, ¿qué licencia saco?")
        if c2.form_submit_button("Preguntar", type="primary", use_container_width=True):
            st.session_state.pregunta = texto
with tab_voz:
    if not API_KEY:
        st.info("La voz necesita conexión con la IA. Por ahora, escribe tu pregunta.")
    else:
        audio = st.audio_input("Toca el micrófono y cuéntale a Wayki qué trámite necesitas")
        if audio is not None:
            with st.spinner("Escuchando…"):
                try:
                    st.session_state.pregunta = transcribir(audio.getvalue(), API_KEY)
                    st.success(f"Entendí: “{st.session_state.pregunta}”")
                except Exception as ex:  # red o cuota
                    st.error(f"No pude escuchar el audio ({ex}). Prueba escribiendo.")

# ---------------------------------------------------------------- respuesta
pregunta = st.session_state.pregunta.strip()
resultados, ans = [], None
if pregunta:
    resultados = buscador.buscar(pregunta, k=5)
    if not resultados:
        st.markdown(f"""<div class="aviso">🤔 No encontré ese trámite en el TUPA de <b>{e(m['corto'])}</b>
            ({len(buscador.procs)} procedimientos). Te recomiendo consultar en mesa de partes
            de la municipalidad.</div>""", unsafe_allow_html=True)
    else:
        if API_KEY:
            with st.spinner("Leyendo el TUPA por ti…"):
                try:
                    ans = respuesta_ia(pregunta, slug, resultados, m["nombre"])
                except Exception as ex:
                    st.caption(f"La IA no respondió ({ex}); te muestro la ficha directa del TUPA.")
                    ans = ficha_sin_ia(resultados[0], m["nombre"])
        else:
            ans = ficha_sin_ia(resultados[0], m["nombre"])

        if not ans.get("encontrado", True):
            st.markdown(f"""<div class="aviso">🤔 {e(ans.get('resumen') or 'No encontré ese trámite en el TUPA.')}
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="resp-titulo">{e(ans.get('procedimiento', ''))}</div>
            <div class="resp-resumen">{e(ans.get('resumen', ''))}</div>
            <div class="fichas">
              <div class="ficha"><div class="ico">💰</div><div class="lab">Costo</div>
                   <div class="val">{e(ans.get('costo') or '—')}</div></div>
              <div class="ficha"><div class="ico">⏱️</div><div class="lab">Plazo</div>
                   <div class="val">{e(ans.get('plazo') or '—')}</div></div>
              <div class="ficha donde"><div class="ico">📍</div><div class="lab">Dónde</div>
                   <div class="val">{e(ans.get('donde') or '—')}</div></div>
            </div>""", unsafe_allow_html=True)

            reqs = ans.get("requisitos") or []
            if reqs:
                st.markdown('<div class="etiqueta">📋 Lleva esto (márcalo cuando lo tengas)</div>',
                            unsafe_allow_html=True)
                for i, req in enumerate(reqs, 1):
                    st.checkbox(req, key=f"req{slug}{i}{hash(pregunta)}")
            if ans.get("consejo"):
                st.markdown(f'<div class="consejo">💡 <b>Consejo:</b> {e(ans["consejo"])}</div>',
                            unsafe_allow_html=True)
            codigo = f" · Código {e(ans['codigo'])}" if ans.get("codigo") else ""
            st.markdown(f"""<div class="fuente">✔ <span><b>Fuente oficial:</b> TUPA de la {e(m['nombre'])},
                págs. {e(str(ans.get('pagina_tupa', '')))}{codigo} ·
                <a href="{e(m['url'])}" target="_blank">ver PDF</a></span></div>""", unsafe_allow_html=True)

            # ---- acciones para el vecino: escuchar, compartir, llegar
            lista = "\n".join(f"☐ {r}" for r in reqs)
            hablado = (f"{ans.get('procedimiento', '')}. Costo: {ans.get('costo', '')}. "
                       f"Plazo: {ans.get('plazo', '')}. Lleva: {'; '.join(reqs)}. "
                       f"Dónde: {ans.get('donde', '')}. {ans.get('consejo', '')}")
            boton_escuchar(hablado)
            wa_txt = (f"*{ans.get('procedimiento', '')}* ({m['corto']})\n"
                      f"💰 Costo: {ans.get('costo', '')}\n⏱️ Plazo: {ans.get('plazo', '')}\n"
                      f"📍 Dónde: {ans.get('donde', '')}\n📋 Lleva:\n{lista}\n"
                      f"Fuente: TUPA, págs. {ans.get('pagina_tupa', '')}\nConsultado en Wayki: {APP_URL}")
            wa = "https://wa.me/?text=" + urllib.parse.quote(wa_txt)
            mapa = "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(
                f"{m['nombre']}, Huancayo, Junín, Perú")
            st.markdown(f"""<div class="acciones">
                <a class="wa" href="{e(wa)}" target="_blank">📲 Enviar por WhatsApp</a>
                <a href="{e(mapa)}" target="_blank">🗺️ Cómo llegar</a></div>""", unsafe_allow_html=True)

            # ---- ¿te sirvió? (métrica para la municipalidad)
            st.markdown('<div class="etiqueta">¿Te sirvió esta respuesta?</div>', unsafe_allow_html=True)
            clave_fb = f"fb_{slug}_{hash(pregunta)}"
            voto = st.feedback("thumbs", key=clave_fb)
            if voto is not None and not st.session_state.get(clave_fb + "_ok"):
                guardar_feedback(slug, pregunta, ans.get("procedimiento", ""), voto == 1)
                st.session_state[clave_fb + "_ok"] = True
            if st.session_state.get(clave_fb + "_ok"):
                st.caption("¡Gracias! Tu respuesta ayuda a la municipalidad a mejorar la orientación.")

        if len(resultados) > 1:
            with st.expander("🔎 Otros trámites parecidos"):
                for r in resultados[1:]:
                    st.write(f"• {r.proc['nombre']} — pág. {r.proc['paginas']}")

# ---------------------------------------------------------------- cómo funciona + transparencia
st.markdown('<div class="etiqueta">Cómo funciona</div>', unsafe_allow_html=True)
st.markdown(f"""
<div class="pasos">
  <div class="paso"><b>1 · Leemos</b>El TUPA oficial del Portal de Transparencia, aunque sea un PDF escaneado (OCR).</div>
  <div class="paso"><b>2 · Buscamos</b>Los procedimientos que responden a tu pregunta, entre {TOTAL} indexados.</div>
  <div class="paso"><b>3 · Explicamos</b>La IA lo resume en simple, solo con el TUPA, y te cita la página.</div>
</div>""", unsafe_allow_html=True)

with st.expander("🔍 Transparencia: datos y lo que leyó la IA"):
    st.write(f"**Municipalidad:** {m['nombre']}")
    st.write(f"**Fuente:** {m['fuente']} · **Norma:** {m['norma']}")
    st.write(f"**Extracción:** {m.get('extraccion', '')} · **Procedimientos:** {len(buscador.procs)}")
    st.markdown(f"[PDF original]({m['url']}) · [Portal de Transparencia]({m['portal']})")
    st.write("🟢 IA activa (Llama 3.3 + Whisper vía Groq)" if API_KEY
             else "🟡 Modo sin IA: se muestra la ficha directa del TUPA")
    if resultados:
        st.caption("Fragmentos del TUPA que recibió el modelo (búsqueda TF-IDF):")
        for r in resultados:
            with st.expander(f"{r.score:.2f} · {r.proc['nombre'][:80]} (pág. {r.proc['paginas']})"):
                st.text(r.proc["texto"][:3000])
    fb = resumen_feedback(slug)
    if fb:
        st.write(f"👍 Utilidad en esta sesión del servidor: {fb[1]} de {fb[0]} votos útiles "
                 f"({100 * fb[1] // fb[0]} %)")
    if ans and "_tokens" in ans:
        st.json(ans["_tokens"])

st.markdown('<div class="pie">Wayki orienta, no reemplaza la atención oficial. Confirma los montos en caja '
            'de la municipalidad. · Proyecto Q-Lab PUCP 2026</div>', unsafe_allow_html=True)
