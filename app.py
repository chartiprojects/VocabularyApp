import json
import os
import random
from datetime import date, timedelta
import streamlit as st

# --- 1. CONFIGURACIÓN Y CARGA DE DATOS ---
DATA_FILE = "vocabulario.json"


def cargar_datos():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "palabras": [],  # Formato: {"es": "", "en": "", "fallada": False, "aciertos_recuperacion": 0}
        "racha": 0,
        "ultima_fecha_examen": None,
    }


def guardar_datos(datos):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=4)


# Cargar datos en la sesión
if "datos" not in st.session_state:
    st.session_state.datos = cargar_datos()

# Estado de navegación entre pantallas
if "pantalla" not in st.session_state:
    st.session_state.pantalla = "menu"

datos = st.session_state.datos

# --- 2. GESTIÓN DE RACHA DIARIA (00:00 - 23:59) ---
hoy = str(date.today())
ayer = str(date.today() - timedelta(days=1))

if datos["ultima_fecha_examen"]:
    if datos["ultima_fecha_examen"] not in [hoy, ayer]:
        datos["racha"] = 0
        guardar_datos(datos)

# Estilos CSS personalizados para botones grandes y diseño móvil
st.markdown(
    """
    <style>
    div.stButton > button {
        width: 100%;
        height: 3.5rem;
        font-size: 1.1rem !important;
        font-weight: bold;
        border-radius: 12px;
        margin-bottom: 10px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- 3. PANTALLAS ---

# ----------------- PANTALLA: MENÚ PRINCIPAL -----------------
if st.session_state.pantalla == "menu":
    col_titulo, col_racha = st.columns([2, 1])
    with col_titulo:
        st.title("🇬🇧 Vocabulario")
    with col_racha:
        st.metric(label="Racha", value=f"🔥 {datos['racha']}")

    st.markdown("---")
    st.subheader("Selecciona una opción:")

    if st.button("➕ Añadir Palabra"):
        st.session_state.pantalla = "add"
        st.rerun()

    if st.button("📝 Examen Diario"):
        st.session_state.pantalla = "examen"
        st.rerun()

    if st.button("📊 Ver Vocabulario"):
        st.session_state.pantalla = "lista"
        st.rerun()


# ----------------- PANTALLA: AÑADIR PALABRA -----------------
elif st.session_state.pantalla == "add":
    st.title("➕ Añadir palabra")

    with st.form("form_add_word", clear_on_submit=True):
        esp = st.text_input("Español").strip().lower()
        ing = st.text_input("Inglés").strip().lower()
        submit = st.form_submit_button("Guardar palabra")

        if submit:
            if not esp or not ing:
                st.error("⚠️ Rellena ambos campos.")
            elif any(p["es"] == esp for p in datos["palabras"]):
                st.warning("⚠️ Esa palabra ya está en tu lista.")
            else:
                nueva_palabra = {
                    "es": esp,
                    "en": ing,
                    "fallada": False,
                    "aciertos_recuperacion": 0,
                }
                datos["palabras"].append(nueva_palabra)
                guardar_datos(datos)
                st.success(f"✅ Palabra añadida: '{esp}' -> '{ing}'")

    st.markdown("---")
    if st.button("🏠 Volver al Menú Principal"):
        st.session_state.pantalla = "menu"
        st.rerun()


# ----------------- PANTALLA: EXAMEN DIARIO -----------------
elif st.session_state.pantalla == "examen":
    st.title("📝 Examen Diario")

    if datos["ultima_fecha_examen"] == hoy:
        st.success("🎉 ¡Ya has completado tu examen de hoy!")
        st.info("Vuelve mañana (a partir de las 00:00) para mantener tu racha.")
        if st.button("🏠 Volver al Menú Principal"):
            st.session_state.pantalla = "menu"
            st.rerun()
    else:
        if "examen_preguntas" not in st.session_state:
            lista_generales = [
                p for p in datos["palabras"] if not p["fallada"]
            ]
            lista_falladas = [p for p in datos["palabras"] if p["fallada"]]

            if len(lista_generales) < 5 or len(lista_falladas) < 5:
                st.warning(
                    "⚠️ Necesitas al menos 5 palabras en la lista general y 5 en el repositorio de fallos para realizar el examen."
                )
                st.caption(
                    f"Tienes actualmente: {len(lista_generales)} generales / {len(lista_falladas)} en fallos."
                )
                if st.button("🏠 Volver al Menú Principal"):
                    st.session_state.pantalla = "menu"
                    st.rerun()
            else:
                bloque_1 = random.sample(lista_generales, 5)
                bloque_2 = random.sample(lista_falladas, 5)
                st.session_state.examen_preguntas = bloque_1 + bloque_2
                st.session_state.respuestas_usuario = {}

        if "examen_preguntas" in st.session_state:
            if "examen_completado" not in st.session_state:
                st.write("Responde a las 10 preguntas:")

                with st.form("form_examen"):
                    for idx, p in enumerate(
                        st.session_state.examen_preguntas, start=1
                    ):
                        st.write(
                            f"**Pregunta {idx}:** ¿Cómo se dice **'{p['es']}'**?"
                        )
                        st.session_state.respuestas_usuario[idx] = (
                            st.text_input("Inglés:", key=f"q_{idx}")
                        )

                    enviar = st.form_submit_button("Enviar Examen")

                if enviar:
                    aciertos_totales = 0

                    for idx, p in enumerate(
                        st.session_state.examen_preguntas, start=1
                    ):
                        resp = (
                            st.session_state.respuestas_usuario[idx]
                            .strip()
                            .lower()
                        )
                        correcta = p["en"].strip().lower()
                        palabra_ref = next(
                            item
                            for item in datos["palabras"]
                            if item["es"] == p["es"]
                        )

                        if resp == correcta:
                            aciertos_totales += 1
                            st.write(f"✅ **{p['es']}**: ¡Correcto!")
                            if palabra_ref["fallada"]:
                                palabra_ref["aciertos_recuperacion"] += 1
                                if palabra_ref["aciertos_recuperacion"] >= 3:
                                    palabra_ref["fallada"] = False
                                    palabra_ref["aciertos_recuperacion"] = 0
                                    st.caption(
                                        f"🎓 ¡'{p['es']}' graduada y devuelta a la lista general!"
                                    )
                        else:
                            st.write(f"❌ **{p['es']}**: Era *{correcta}*")
                            palabra_ref["fallada"] = True
                            palabra_ref["aciertos_recuperacion"] = 0

                    if datos["ultima_fecha_examen"] == ayer:
                        datos["racha"] += 1
                    else:
                        datos["racha"] = 1

                    datos["ultima_fecha_examen"] = hoy
                    guardar_datos(datos)

                    st.session_state.examen_completado = True
                    st.session_state.nota_final = aciertos_totales
                    st.rerun()

            else:
                st.balloons()
                st.success("🔥 **+1 DÍA DE RACHA CONSEGUIDO** 🔥")
                st.subheader(
                    f"Resultado: {st.session_state.nota_final} / 10 aciertos"
                )

                if st.button("🏠 Volver al Menú Principal"):
                    del st.session_state.examen_preguntas
                    del st.session_state.examen_completado
                    del st.session_state.nota_final
                    st.session_state.pantalla = "menu"
                    st.rerun()


# ----------------- PANTALLA: VER VOCABULARIO -----------------
elif st.session_state.pantalla == "lista":
    st.title("📊 Tu Vocabulario")

    tab1, tab2 = st.tabs(["🟢 Generales", "🔴 Repositorio de Fallos"])

    with tab1:
        generales = [p for p in datos["palabras"] if not p["fallada"]]
        if generales:
            for p in generales:
                st.write(f"• **{p['es']}** ➔ *{p['en']}*")
        else:
            st.info("No hay palabras generales aún.")

    with tab2:
        falladas = [p for p in datos["palabras"] if p["fallada"]]
        if falladas:
            for p in falladas:
                st.write(
                    f"• **{p['es']}** ➔ *{p['en']}* *(Aciertos: {p['aciertos_recuperacion']}/3)*"
                )
        else:
            st.info("¡Excelente! No tienes palabras pendientes por corregir.")

    st.markdown("---")
    if st.button("🏠 Volver al Menú Principal"):
        st.session_state.pantalla = "menu"
        st.rerun()
