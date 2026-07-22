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

# Estilos CSS personalizados
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

    if st.button("📊 Ver / Editar Vocabulario"):
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
                st.success(f"✅ Palabra añadida: '{esp.capitalize()}' -> '{ing}'")

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
                                "tu_resp": resp,
                                "correcta": correcta,
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
                                "tu_resp": resp if resp else "(Vacío)",
                                "correcta": correcta,
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


# ----------------- PANTALLA: VER Y EDITAR VOCABULARIO -----------------
elif st.session_state.pantalla == "lista":
    st.title("📊 Tu Vocabulario")

    tab1, tab2 = st.tabs(["🟢 Generales", "🔴 Repositorio de Fallos"])

    def mostrar_tabla_ordenada(lista_palabras):
        # Ordenar alfabéticamente por la palabra en inglés ('en')
        lista_ordenada = sorted(lista_palabras, key=lambda x: x["en"].lower())

        # Cabecera de la tabla
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            st.markdown("**Inglés (A-Z)**")
        with c2:
            st.markdown("**Español**")
        with c3:
            st.markdown("**Acción**")
        st.markdown("---")

        # Filas ordenadas
        for idx, p in enumerate(lista_ordenada):
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                st.write(f"🔤 **{p['en']}**")
            with col2:
                # Si está en falladas, muestra los aciertos acumulados
                extra = f" *({p['aciertos_recuperacion']}/3)*" if p["fallada"] else ""
                st.write(f"{p['es'].capitalize()}{extra}")
            with col3:
                # Desplegable para editar
                with st.expander("✏️"):
                    with st.form(f"edit_form_{p['es']}_{idx}"):
                        nuevo_es = st.text_input("Español", value=p["es"]).strip().lower()
                        nuevo_en = st.text_input("Inglés", value=p["en"]).strip().lower()
                        guardar_edit = st.form_submit_button("Guardar")

                        if guardar_edit:
                            if nuevo_es and nuevo_en:
                                p["es"] = nuevo_es
                                p["en"] = nuevo_en
                                guardar_datos(datos)
                                st.success("✅ Guardado")
                                st.rerun()
                            else:
                                st.error("Sin campos vacíos")

    with tab1:
        generales = [p for p in datos["palabras"] if not p["fallada"]]
        if generales:
            mostrar_tabla_ordenada(generales)
        else:
            st.info("No hay palabras generales aún.")

    with tab2:
        falladas = [p for p in datos["palabras"] if p["fallada"]]
        if falladas:
            mostrar_tabla_ordenada(falladas)
        else:
            st.info("¡Excelente! No tienes palabras pendientes por corregir.")

    st.markdown("---")
    if st.button("🏠 Volver al Menú Principal"):
        st.session_state.pantalla = "menu"
        st.rerun()
