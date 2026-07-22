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

datos = st.session_state.datos

# --- 2. GESTIÓN DE RACHA DIARIA ---
hoy = str(date.today())
ayer = str(date.today() - timedelta(days=1))

if datos["ultima_fecha_examen"]:
    if datos["ultima_fecha_examen"] not in [hoy, ayer]:
        datos["racha"] = 0
        guardar_datos(datos)

# --- 3. INTERFAZ Y NAVEGACIÓN ---
st.title("🇬🇧 Vocabulario Diario")
st.sidebar.metric(label="🔥 Racha Actual", value=f"{datos['racha']} días")

opcion = st.sidebar.radio(
    "Menú principal",
    ["➕ Añadir Palabras", "📝 Examen Diario", "📊 Ver Vocabulario"],
)

# --- SECCIÓN: AÑADIR PALABRAS ---
if opcion == "➕ Añadir Palabras":
    st.header("Añadir nueva palabra")

    with st.form("form_add_word", clear_on_submit=True):
        esp = st.text_input("Español").strip().lower()
        ing = st.text_input("Inglés").strip().lower()
        submit = st.form_submit_button("Guardar palabra")

        if submit and esp and ing:
            if any(p["es"] == esp for p in datos["palabras"]):
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
                st.success(f"✅ ¡Guardada! '{esp}' -> '{ing}'")

# --- SECCIÓN: EXAMEN DIARIO ---
elif opcion == "📝 Examen Diario":
    st.header("Examen Diario")

    if datos["ultima_fecha_examen"] == hoy:
        st.success(
            "🎉 ¡Ya has completado tu examen de hoy! Vuelve mañana para mantener tu racha."
        )
    else:
        if "examen_preguntas" not in st.session_state:
            lista_generales = [
                p for p in datos["palabras"] if not p["fallada"]
            ]
            lista_falladas = [p for p in datos["palabras"] if p["fallada"]]

            if len(lista_generales) < 5:
                st.info(
                    f"Necesitas al menos 5 palabras normales para el examen (tienes {len(lista_generales)})."
                )
            elif len(lista_falladas) < 5:
                st.info(
                    f"Necesitas al menos 5 palabras en el repositorio de fallos para completar el bloque de reforzamiento (tienes {len(lista_falladas)})."
                )
            else:
                bloque_1 = random.sample(lista_generales, 5)
                bloque_2 = random.sample(lista_falladas, 5)

                st.session_state.examen_preguntas = bloque_1 + bloque_2
                st.session_state.respuestas_usuario = {}

        if "examen_preguntas" in st.session_state:
            st.write("Responde a las siguientes 10 preguntas:")

            with st.form("form_examen"):
                for idx, p in enumerate(
                    st.session_state.examen_preguntas, start=1
                ):
                    st.subheader(
                        f"Pregunta {idx}: ¿Cómo se dice **'{p['es']}'** en inglés?"
                    )
                    st.session_state.respuestas_usuario[idx] = st.text_input(
                        "Tu respuesta:", key=f"q_{idx}"
                    )

                enviar_examen = st.form_submit_button("Enviar Examen")

            if enviar_examen:
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
                                st.balloons()
                                st.caption(
                                    f"🎓 ¡La palabra '{p['es']}' se ha graduado y vuelve a la lista general!"
                                )
                    else:
                        st.write(
                            f"❌ **{p['es']}**: Incorrecto (Era: *{correcta}*)"
                        )
                        palabra_ref["fallada"] = True
                        palabra_ref["aciertos_recuperacion"] = 0

                if datos["ultima_fecha_examen"] == ayer:
                    datos["racha"] += 1
                elif (
                    datos["ultima_fecha_examen"] is None
                    or datos["ultima_fecha_examen"] != hoy
                ):
                    datos["racha"] = 1

                datos["ultima_fecha_examen"] = hoy
                guardar_datos(datos)

                del st.session_state.examen_preguntas
                st.success(
                    f"Examen finalizado. Nota: {aciertos_totales}/10. ¡Racha actualizada!"
                )

# --- SECCIÓN: VER VOCABULARIO ---
elif opcion == "📊 Ver Vocabulario":
    st.header("Tu repositorio de palabras")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🟢 Generales")
        for p in datos["palabras"]:
            if not p["fallada"]:
                st.write(f"• **{p['es']}** : {p['en']}")

    with col2:
        st.subheader("🔴 En Repositorio de Fallos")
        for p in datos["palabras"]:
            if p["fallada"]:
                st.write(
                    f"• **{p['es']}** : {p['en']} *(Aciertos: {p['aciertos_recuperacion']}/3)*"
                )
