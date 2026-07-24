import random
from datetime import date, timedelta
import pandas as pd
import streamlit as st
from supabase import create_client

# --- 1. CONEXIÓN A SUPABASE ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def cargar_datos():
    palabras_res = supabase.table("vocabulario").select("*").execute()
    estado_res = supabase.table("estado_app").select("*").eq("id", 1).execute()

    palabras = palabras_res.data if palabras_res.data else []
    estado = (
        estado_res.data[0]
        if estado_res.data
        else {"racha": 0, "ultima_fecha_examen": None}
    )

    return {
        "palabras": palabras,
        "racha": estado["racha"],
        "ultima_fecha_examen": estado["ultima_fecha_examen"],
    }


def guardar_palabra_bd(es, en):
    supabase.table("vocabulario").insert({"es": es, "en": en}).execute()


def actualizar_palabra_bd(id_palabra, datos_actualizar):
    supabase.table("vocabulario").update(datos_actualizar).eq(
        "id", id_palabra
    ).execute()


def actualizar_estado_bd(racha, fecha):
    supabase.table("estado_app").update(
        {"racha": racha, "ultima_fecha_examen": fecha}
    ).eq("id", 1).execute()


# Cargar datos en la sesión
if "datos" not in st.session_state:
    st.session_state.datos = cargar_datos()

if "pantalla" not in st.session_state:
    st.session_state.pantalla = "menu"

datos = st.session_state.datos

# --- 2. GESTIÓN DE RACHA DIARIA ---
hoy = str(date.today())
ayer = str(date.today() - timedelta(days=1))

if datos["ultima_fecha_examen"]:
    if datos["ultima_fecha_examen"] not in [hoy, ayer]:
        datos["racha"] = 0
        actualizar_estado_bd(0, datos["ultima_fecha_examen"])

# Estilos CSS
st.markdown(
    """
    <style>
    div.stButton { display: flex; justify-content: center; }
    div.stButton > button {
        width: 100% !important; max-width: 400px; height: 3.5rem;
        font-size: 1.1rem !important; font-weight: bold; border-radius: 12px; margin-bottom: 12px;
    }
    .titulo-centrado { text-align: center; margin-bottom: 1rem; }
    </style>
""",
    unsafe_allow_html=True,
)

# --- 3. PANTALLAS ---

# ----------------- PANTALLA: MENÚ PRINCIPAL -----------------
if st.session_state.pantalla == "menu":
    col_titulo, col_racha = st.columns([2, 1])
    with col_titulo:
        st.markdown(
            "<h1 class='titulo-centrado'>🇬🇧 Vocabulario</h1>",
            unsafe_allow_html=True,
        )
    with col_racha:
        st.metric(label="Racha", value=f"🔥 {datos['racha']}")

    st.markdown("---")

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
                guardar_palabra_bd(esp, ing)
                st.session_state.datos = cargar_datos()
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

    if datos["ultima_fecha_examen"] == hoy and "resumen_resultados" not in st.session_state:
        st.success("🎉 ¡Ya has completado tu examen de hoy!")
        st.info("Vuelve mañana para mantener tu racha.")
        if st.button("🏠 Volver al Menú Principal"):
            st.session_state.pantalla = "menu"
            st.rerun()
    else:
        # Preparamos las preguntas si es un examen nuevo
        if "examen_preguntas" not in st.session_state and "resumen_resultados" not in st.session_state:
            lista_todas = datos["palabras"]
            lista_falladas = [p for p in datos["palabras"] if p["fallada"]]

            if len(lista_todas) < 10:
                st.warning(
                    f"⚠️ Necesitas al menos 10 palabras guardadas para hacer el examen (tienes {len(lista_todas)})."
                )
                if st.button("🏠 Volver al Menú Principal"):
                    st.session_state.pantalla = "menu"
                    st.rerun()
            else:
                num_falladas_a_coger = min(5, len(lista_falladas))
                bloque_falladas = random.sample(lista_falladas, num_falladas_a_coger)

                palabras_restantes = [p for p in lista_todas if p not in bloque_falladas]
                num_generales_necesarias = 10 - len(bloque_falladas)

                bloque_generales = random.sample(palabras_restantes, num_generales_necesarias)

                preguntas_examen = bloque_falladas + bloque_generales
                random.shuffle(preguntas_examen)

                st.session_state.examen_preguntas = preguntas_examen

        # PANTALLA 1: HACIENDO EL EXAMEN
        if "resumen_resultados" not in st.session_state and "examen_preguntas" in st.session_state:
            st.write("Escribe la traducción en inglés:")

            with st.form("form_examen"):
                respuestas_temp = {}
                for idx, p in enumerate(st.session_state.examen_preguntas, start=1):
                    respuestas_temp[idx] = st.text_input(
                        f"{idx}. {p['es'].capitalize()}", key=f"q_{idx}"
                    )

                enviar = st.form_submit_button("Enviar Examen")

            if enviar:
                aciertos_totales = 0
                resumen_resultados = []

                for idx, p in enumerate(st.session_state.examen_preguntas, start=1):
                    resp = respuestas_temp[idx].strip().lower()
                    correcta = p["en"].strip().lower()

                    if resp == correcta:
                        aciertos_totales += 1
                        resumen_resultados.append({
                            "es": p["es"].capitalize(),
                            "tu_resp": resp.capitalize(),
                            "correcta": correcta.capitalize(),
                            "es_correcto": True,
                        })

                        if p["fallada"]:
                            nuevos_aciertos = p["aciertos_recuperacion"] + 1
                            if nuevos_aciertos >= 3:
                                actualizar_palabra_bd(p["id"], {"fallada": False, "aciertos_recuperacion": 0})
                            else:
                                actualizar_palabra_bd(p["id"], {"aciertos_recuperacion": nuevos_aciertos})
                    else:
                        resumen_resultados.append({
                            "es": p["es"].capitalize(),
                            "tu_resp": resp.capitalize() if resp else "(Vacío)",
                            "correcta": correcta.capitalize(),
                            "es_correcto": False,
                        })
                        actualizar_palabra_bd(p["id"], {"fallada": True, "aciertos_recuperacion": 0})

                nueva_racha = (
                    datos["racha"] + 1
                    if datos["ultima_fecha_examen"] == ayer
                    else 1
                )
                actualizar_estado_bd(nueva_racha, hoy)

                # Guardamos los resultados para mostrarlos en la pantalla de corrección
                st.session_state.datos = cargar_datos()
                st.session_state.nota_final = aciertos_totales
                st.session_state.total_preguntas = len(st.session_state.examen_preguntas)
                st.session_state.resumen_resultados = resumen_resultados
                st.rerun()

        # PANTALLA 2: MOSTRAR CORRECCIÓN DETALLADA
        elif "resumen_resultados" in st.session_state:
            st.balloons()
            st.success("🔥 **+1 DÍA DE RACHA CONSEGUIDO** 🔥")
            st.subheader(
                f"Resultado: {st.session_state.nota_final} / {st.session_state.total_preguntas} aciertos"
            )

            st.markdown("---")
            st.subheader("📋 Corrección del Examen:")

            # Bloques explícitos en Verde y Rojo
            for item in st.session_state.resumen_resultados:
                if item["es_correcto"]:
                    st.success(
                        f"✅ **{item['es']}**: {item['tu_resp']} *(¡Correcto!)*"
                    )
                else:
                    st.error(
                        f"❌ **{item['es']}**: Tu respuesta: ~~{item['tu_resp']}~~ ➔ **Correcta: {item['correcta']}**"
                    )

            st.markdown("---")
            if st.button("🏠 Volver al Menú Principal"):
                if "examen_preguntas" in st.session_state:
                    del st.session_state.examen_preguntas
                if "resumen_resultados" in st.session_state:
                    del st.session_state.resumen_resultados
                if "nota_final" in st.session_state:
                    del st.session_state.nota_final
                if "total_preguntas" in st.session_state:
                    del st.session_state.total_preguntas
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
                            actualizar_palabra_bd(
                                palabra_sel["id"],
                                {"en": edit_ing, "es": edit_esp},
                            )
                            st.session_state.datos = cargar_datos()
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
        construir_vista_tabla(datos["palabras"], "generales")

    with tab2:
        falladas = [p for p in datos["palabras"] if p["fallada"]]
        construir_vista_tabla(falladas, "falladas")

    st.markdown("---")
    if st.button("🏠 Volver al Menú Principal"):
        st.session_state.pantalla = "menu"
        st.rerun()
