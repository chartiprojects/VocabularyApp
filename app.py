import json
import os
import random
from datetime import date, timedelta
import pandas as pd
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

# Estilos CSS personalizados para centrar botones y títulos
st.markdown(
    """
    <style>
    /* Estilo y centrado de botones */
    div.stButton {
        display: flex;
        justify-content: center;
    }
    div.stButton > button {
        width: 100% !important;
        max-width: 400px;
        height: 3.5rem;
        font-size: 1.1rem !important;
        font-weight: bold;
        border-radius: 12px;
        margin-bottom: 12px;
    }
    .titulo-centrado {
        text-align: center;
        margin-bottom: 1rem;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- 3. PANTALLAS ---

# ----------------- PANTALLA: MENÚ PRINCIPAL -----------------
if st.session_state.pantalla == "menu":
    # Restaurada la cabecera tal como estaba en el paso anterior
    col_titulo, col_racha = st.columns([2, 1])
    with col_titulo:
        st.markdown(
            "<h1 class='titulo-centrado'>🇬🇧 Vocabulario</h1>",
            unsafe_allow_html=True,
        )
    with col_racha:
        st.metric(label="Racha", value=f"🔥 {datos['racha']}")

    st.markdown("---")

    # Botones centrados
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
    st.markdown(
        "<h1 class='titulo-centrado'>➕ Añadir palabra</h1>",
        unsafe_allow_html=True,
    )

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
                st.success(
                    f"✅ Palabra añadida: '{esp.capitalize()}' -> '{ing.capitalize()}'"
                )

    st.markdown("---")
    if st.button("🏠 Volver al Menú Principal"):
        st.session_state.pantalla = "menu"
        st.rerun()


# ----------------- PANTALLA: EXAMEN DIARIO -----------------
elif st.session_state.pantalla == "examen":
    st.markdown(
        "<h1 class='titulo-centrado'>📝 Examen Diario</h1>",
        unsafe_allow_html=True,
    )

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

            if len(datos["palabras"]) < 10:
                st.warning(
                    f"⚠️ Necesitas al menos 10 palabras guardadas para poder hacer el examen (tienes {len(datos['palabras'])})."
                )
                if st.button("🏠 Volver al Menú Principal"):
                    st.session_state.pantalla = "menu"
                    st.rerun()
            else:
                num_falladas_a_coger = min(5, len(lista_falladas))
                bloque_falladas = random.sample(
                    lista_falladas, num_falladas_a_coger
                )

                num_generales_necesarias = 10 - len(bloque_falladas)

                if len(lista_generales) >= num_generales_necesarias:
                    bloque_generales = random.sample(
                        lista_generales, num_generales_necesarias
                    )
                else:
                    bloque_generales = lista_generales

                preguntas_examen = bloque_falladas + bloque_generales
                random.shuffle(preguntas_examen)

                st.session_state.examen_preguntas = preguntas_examen
                st.session_state.respuestas_usuario = {}

        if "examen_preguntas" in st.session_state:
            if "examen_completado" not in st.session_state:
                st.write("Escribe la traducción en inglés:")

                with st.form("form_examen"):
                    for idx, p in enumerate(
                        st.session_state.examen_preguntas, start=1
                    ):
                        palabra_es_capital = p["es"].capitalize()
                        st.text_input(
                            f"{idx}. {palabra_es_capital}", key=f"q_{idx}"
                        )

                    enviar = st.form_submit_button("Enviar Examen")

                if enviar:
                    aciertos_totales = 0
                    resumen_resultados = []

                    for idx, p in enumerate(
                        st.session_state.examen_preguntas, start=1
                    ):
                        resp = (
                            st.session_state.get(f"q_{idx}", "")
                            .strip()
                            .lower()
                        )
                        correcta = p["en"].strip().lower()
                        palabra_ref = next(
                            item
                            for item in datos["palabras"]
                            if item["es"] == p["es"]
                        )

                        es_correcto = resp == correcta

                        if es_correcto:
                            aciertos_totales += 1
                            resumen_resultados.append({
                                "es": p["es"].capitalize(),
                                "tu_resp": resp.capitalize(),
                                "correcta": correcta.capitalize(),
                                "es_correcto": True,
                            })
                            if palabra_ref["fallada"]:
                                palabra_ref["aciertos_recuperacion"] += 1
                                if palabra_ref["aciertos_recuperacion"] >= 3:
                                    palabra_ref["fallada"] = False
                                    palabra_ref["aciertos_recuperacion"] = 0
                        else:
                            resumen_resultados.append({
                                "es": p["es"].capitalize(),
                                "tu_resp": (
                                    resp.capitalize() if resp else "(Vacío)"
                                ),
                                "correcta": correcta.capitalize(),
                                "es_correcto": False,
                            })
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
                    st.session_state.total_preguntas = len(
                        st.session_state.examen_preguntas
                    )
                    st.session_state.resumen_resultados = resumen_resultados
                    st.rerun()

            else:
                st.balloons()
                st.success("🔥 **+1 DÍA DE RACHA CONSEGUIDO** 🔥")
                st.subheader(
                    f"Resultado: {st.session_state.nota_final} / {st.session_state.total_preguntas} aciertos"
                )

                st.markdown("---")
                st.subheader("📋 Resumen del Examen:")

                for item in st.session_state.resumen_resultados:
                    if item["es_correcto"]:
                        st.markdown(
                            f"✅ **{item['es']}**: {item['tu_resp']} *(¡Correcto!)*"
                        )
                    else:
                        st.markdown(
                            f"❌ **{item['es']}**: Tu respuesta: ~~{item['tu_resp']}~~ ➔ **Correcta: {item['correcta']}**"
                        )

                st.markdown("---")
                if st.button("🏠 Volver al Menú Principal"):
                    del st.session_state.examen_preguntas
                    del st.session_state.examen_completado
                    del st.session_state.nota_final
                    del st.session_state.total_preguntas
                    del st.session_state.resumen_resultados
                    st.session_state.pantalla = "menu"
                    st.rerun()


# ----------------- PANTALLA: VER VOCABULARIO -----------------
elif st.session_state.pantalla == "lista":
    st.markdown(
        "<h1 class='titulo-centrado'>📊 Tu Vocabulario</h1>",
        unsafe_allow_html=True,
    )

    tab1, tab2 = st.tabs(["🟢 Generales", "🔴 Repositorio de Fallos"])

    def construir_vista_tabla(lista_palabras, clave_modo):
        if not lista_palabras:
            st.info("No hay palabras en esta categoría.")
            return

        with st.expander("✏️ Editar una palabra de esta lista"):
            opciones_editar = [
                f"{p['en'].capitalize()} -> {p['es'].capitalize()}"
                for p in lista_palabras
            ]
            seleccion = st.selectbox(
                "Elige la palabra a modificar:",
                opciones_editar,
                key=f"select_{clave_modo}",
            )

            if seleccion:
                idx_sel = opciones_editar.index(seleccion)
                palabra_sel = lista_palabras[idx_sel]

                with st.form(f"form_editar_{clave_modo}"):
                    edit_ing = (
                        st.text_input("Inglés", value=palabra_sel["en"])
                        .strip()
                        .lower()
                    )
                    edit_esp = (
                        st.text_input("Español", value=palabra_sel["es"])
                        .strip()
                        .lower()
                    )
                    btn_guardar = st.form_submit_button("Guardar Cambios")

                    if btn_guardar:
                        if edit_ing and edit_esp:
                            palabra_sel["en"] = edit_ing
                            palabra_sel["es"] = edit_esp
                            guardar_datos(datos)
                            st.success("✅ ¡Palabra actualizada!")
                            st.rerun()
                        else:
                            st.error("No dejes campos vacíos.")

        lista_ordenada = sorted(lista_palabras, key=lambda x: x["en"].lower())

        df_datos = []
        for p in lista_ordenada:
            fila = {
                "Inglés": p["en"].capitalize(),
                "Español": p["es"].capitalize(),
            }
            if p["fallada"]:
                fila["Aciertos"] = f"{p['aciertos_recuperacion']}/3"
            df_datos.append(fila)

        df = pd.DataFrame(df_datos)
        st.table(df)

    with tab1:
        generales = [p for p in datos["palabras"] if not p["fallada"]]
        construir_vista_tabla(generales, "generales")

    with tab2:
        falladas = [p for p in datos["palabras"] if p["fallada"]]
        construir_vista_tabla(falladas, "falladas")

    st.markdown("---")
    if st.button("🏠 Volver al Menú Principal"):
        st.session_state.pantalla = "menu"
        st.rerun()
