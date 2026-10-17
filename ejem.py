
import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------------------------------------------
# 1. DATOS (ilustrativos). Emisiones en MtCO2e
#    papeleo aburrido
#    solo son datos:v
# ---------------------------------------------------------------
DATOS = pd.DataFrame(
    [
        # país,           iso,  base2015, actual2023, meta_pct, export_ue
        ("Alemania",      "DEU",    900,    700,   55,  55),
        ("Francia",       "FRA",    450,    380,   40,  50),
        ("Estados Unidos","USA",   6200,   5700,   50,  20),
        ("China",         "CHN",  11000,  12600,   10,  16),
        ("India",         "IND",   2900,   3700,    5,  17),
        ("Brasil",        "BRA",   1500,   1450,   30,  18),
        ("México",        "MEX",    700,    720,   35,  10),
        ("Rusia",         "RUS",   2100,   2150,   15,  35),
        ("Japón",         "JPN",   1200,   1070,   46,  12),
        ("Sudáfrica",     "ZAF",    470,    480,   30,  25),
    ],
    columns=["pais", "iso", "base_2015", "actual_2023", "meta_pct", "export_ue"],
)

AÑO_BASE, AÑO_ACTUAL, AÑO_META = 2015, 2023, 2030


# ---------------------------------------------------------------
# 2. logica en el programa
# ---------------------------------------------------------------
def calcular(df: pd.DataFrame, precio_carbono: float, severidad: float) -> pd.DataFrame:
    df = df.copy()
    avance = (AÑO_ACTUAL - AÑO_BASE) / (AÑO_META - AÑO_BASE)

    # Emisiones que debería tener hoy si fuera en línea recta hacia su meta
    df["meta_2030"] = df["base_2015"] * (1 - df["meta_pct"] / 100)
    df["esperado_hoy"] = df["base_2015"] * (1 - df["meta_pct"] / 100 * avance)

    # Brecha actual (%): positivo = va peor de lo prometido
    df["brecha_pct"] = (df["actual_2023"] - df["esperado_hoy"]) / df["esperado_hoy"] * 100

    # Proyección 2030 siguiendo la tendencia actual
    tendencia_anual = (df["actual_2023"] - df["base_2015"]) / (AÑO_ACTUAL - AÑO_BASE)
    df["proyeccion_2030"] = df["base_2015"] + tendencia_anual * (AÑO_META - AÑO_BASE)
    df["exceso_2030"] = (df["proyeccion_2030"] - df["meta_2030"]).clip(lower=0)

    # Estado semáforo
    def estado(b):
        if b <= 0:
            return "✅ Cumple"
        if b <= 10:
            return "⚠️ En riesgo"
        return "❌ Incumple"

    df["estado"] = df["brecha_pct"].apply(estado)

    # -----------------------------------------------------------
    # 3. CONSECUENCIAS DIPLOMÁTICAS (reglas que en teoria deben de seguir
    # -----------------------------------------------------------
    # Arancel de carbono estimado (%) sobre exportaciones a mercados con precio al carbono.
    # Crece con la brecha, con el precio del carbono y con la severidad elegida.
    brecha_pos = df["brecha_pct"].clip(lower=0, upper=50)
    df["arancel_pct"] = (brecha_pos / 50 * (precio_carbono / 100) * 30 * severidad).round(1)

    # Riesgo diplomático 0-100: brecha + dependencia comercial
    riesgo = brecha_pos * 1.5 + df["export_ue"] * 0.5 * (brecha_pos > 0)
    df["riesgo_diplomatico"] = (riesgo * severidad).clip(upper=100).round(0)

    def nivel(r):
        if r >= 60:
            return "Alto: posibles sanciones"
        if r >= 30:
            return "Medio: presión diplomática"
        return "Bajo"

    df["consecuencia"] = df["riesgo_diplomatico"].apply(nivel)
    return df


# ---------------------------------------------------------------
# 4. interfaz protype type99 lol
# ---------------------------------------------------------------
st.set_page_config(page_title="Diplomacy & Climate Tracker", layout="wide")
st.title("🌍 Diplomacy & Climate Tracker")
st.caption("Simulador de cumplimiento del Acuerdo de París · ODS 13 · Datos ilustrativos")

with st.sidebar:
    st.header("Parámetros del escenario")
    precio = st.slider("Precio del carbono (USD/tCO₂)", 20, 200, 80, step=10)
    severidad = st.slider("Severidad diplomática", 0.5, 2.0, 1.0, step=0.1,
                          help="Qué tan duro reacciona la comunidad internacional")
    paises = st.multiselect("Países", DATOS["pais"].tolist(), default=DATOS["pais"].tolist())

df = calcular(DATOS[DATOS["pais"].isin(paises)], precio, severidad)

if df.empty:
    st.warning("Selecciona al menos un país.")
    st.stop()

# matematicas en el programa
c1, c2, c3 = st.columns(3)
c1.metric("Países que cumplen", int((df["brecha_pct"] <= 0).sum()), f"de {len(df)}")
c2.metric("Brecha promedio", f"{df['brecha_pct'].mean():.1f}%")
c3.metric("Riesgo diplomático alto", int((df["riesgo_diplomatico"] >= 60).sum()))

# ---------------------------------------------------------------
# MAPA INTERACTIVO
# ---------------------------------------------------------------
st.subheader("🗺️ Mapa mundial de riesgo diplomático")
mapa_variable = st.radio(
    "Colorear mapa por:",
    ["riesgo_diplomatico", "brecha_pct", "arancel_pct"],
    format_func=lambda x: {
        "riesgo_diplomatico": "🔴 Riesgo diplomático",
        "brecha_pct": "📊 Brecha de cumplimiento (%)",
        "arancel_pct": "💰 Arancel de carbono estimado (%)",
    }[x],
    horizontal=True,
)

titulos_mapa = {
    "riesgo_diplomatico": "Riesgo diplomático por país (0-100)",
    "brecha_pct": "Brecha de cumplimiento por país (%)",
    "arancel_pct": "Arancel de carbono estimado por país (%)",
}

escalas_mapa = {
    "riesgo_diplomatico": "OrRd",
    "brecha_pct": "RdYlGn_r",
    "arancel_pct": "YlOrBr",
}

fig_mapa = px.choropleth(
    df,
    locations="iso",
    color=mapa_variable,
    hover_name="pais",
    hover_data={
        "iso": False,
        "estado": True,
        "brecha_pct": ":.1f",
        "riesgo_diplomatico": ":.0f",
        "arancel_pct": ":.1f",
        "actual_2023": ":.0f",
    },
    color_continuous_scale=escalas_mapa[mapa_variable],
    title=titulos_mapa[mapa_variable],
    labels={
        "riesgo_diplomatico": "Riesgo",
        "brecha_pct": "Brecha %",
        "arancel_pct": "Arancel %",
        "actual_2023": "Emisiones 2023",
        "estado": "Estado",
    },
)
fig_mapa.update_layout(
    geo=dict(
        showframe=False,
        showcoastlines=True,
        coastlinecolor="LightGrey",
        projection_type="natural earth",
    ),
    height=500,
    margin=dict(l=0, r=0, t=40, b=0),
)
st.plotly_chart(fig_mapa, use_container_width=True)

# ---------------------------------------------------------------
# ANÁLISIS NARRATIVO POR PAÍS
# ---------------------------------------------------------------
st.subheader("📝 Análisis detallado por país")
st.caption("Selecciona un país para ver un análisis narrativo de su situación climática y diplomática.")

pais_sel = st.selectbox(
    "🔍 Selecciona un país para analizar:",
    df["pais"].tolist(),
    index=0,
)

fila = df[df["pais"] == pais_sel].iloc[0]

# --- Construir texto narrativo dinámico ---
brecha = fila["brecha_pct"]
riesgo = fila["riesgo_diplomatico"]
arancel = fila["arancel_pct"]
estado = fila["estado"]
proyeccion = fila["proyeccion_2030"]
meta = fila["meta_2030"]
export_ue_val = fila["export_ue"]
actual = fila["actual_2023"]
base = fila["base_2015"]

# Bloque de estado general
if brecha <= 0:
    txt_brecha = (
        f"**{pais_sel}** está **cumpliendo** su trayectoria prometida hacia el Acuerdo de París. "
        f"Sus emisiones actuales ({actual:.0f} MtCO₂e) están por debajo de lo esperado para 2023 "
        f"según su compromiso de reducir un {fila['meta_pct']:.0f}% respecto a 2015. "
        f"Esto significa que el país va **más rápido** de lo necesario en su transición climática."
    )
    emoji_estado = "🟢"
elif brecha <= 10:
    txt_brecha = (
        f"**{pais_sel}** está **en riesgo** de incumplir su meta climática. "
        f"Sus emisiones actuales ({actual:.0f} MtCO₂e) superan en un **{brecha:.1f}%** la trayectoria esperada. "
        f"Aunque la desviación aún es moderada, de continuar esta tendencia podría "
        f"no alcanzar su objetivo de reducir un {fila['meta_pct']:.0f}% para 2030."
    )
    emoji_estado = "🟡"
else:
    txt_brecha = (
        f"**{pais_sel}** **no está cumpliendo** su compromiso climático. "
        f"Sus emisiones actuales ({actual:.0f} MtCO₂e) superan en un **{brecha:.1f}%** "
        f"lo que debería haber logrado hasta ahora. "
        f"Su meta era reducir un {fila['meta_pct']:.0f}% respecto a 2015, pero la tendencia "
        f"apunta a {proyeccion:.0f} MtCO₂e en 2030, muy lejos de la meta de {meta:.0f} MtCO₂e."
    )
    emoji_estado = "🔴"

# Bloque de riesgo diplomático
if riesgo >= 60:
    txt_riesgo = (
        f"El riesgo diplomático de {pais_sel} es **alto ({riesgo:.0f}/100)**. "
        f"Esto se debe a que combina una brecha significativa en emisiones con una dependencia "
        f"comercial relevante: el **{export_ue_val}%** de sus exportaciones van a mercados que aplican "
        f"mecanismos de precio al carbono (como el CBAM europeo). "
        f"En este escenario, {pais_sel} podría enfrentar **sanciones comerciales, aranceles compensatorios** "
        f"de hasta un **{arancel:.1f}%**, y presión diplomática en foros multilaterales como la COP."
    )
elif riesgo >= 30:
    txt_riesgo = (
        f"El riesgo diplomático de {pais_sel} es **medio ({riesgo:.0f}/100)**. "
        f"Aunque la brecha de cumplimiento existe, la combinación con su nivel de exposición "
        f"comercial ({export_ue_val}% de exportaciones a mercados con precio al carbono) genera "
        f"**presión diplomática moderada**. Se estima un arancel compensatorio de aproximadamente "
        f"**{arancel:.1f}%** sobre esas exportaciones. "
        f"Es probable que {pais_sel} reciba llamados a fortalecer sus políticas climáticas, pero "
        f"sin sanciones directas por el momento."
    )
else:
    txt_riesgo = (
        f"El riesgo diplomático de {pais_sel} es **bajo ({riesgo:.0f}/100)**. "
    )
    if brecha <= 0:
        txt_riesgo += (
            f"Al estar cumpliendo con su trayectoria climática, no enfrenta presiones comerciales "
            f"significativas. El arancel estimado es del **{arancel:.1f}%**, es decir, prácticamente nulo."
        )
    else:
        txt_riesgo += (
            f"A pesar de tener una brecha moderada, su baja dependencia de exportaciones a mercados "
            f"con precio al carbono ({export_ue_val}%) mitiga el impacto comercial. "
            f"El arancel estimado sería del **{arancel:.1f}%**."
        )

# Bloque de brecha comercial / impacto económico
variacion = actual - base
if variacion > 0:
    txt_comercial = (
        f"📈 **Impacto económico-comercial:** Desde 2015, las emisiones de {pais_sel} han "
        f"**aumentado en {variacion:.0f} MtCO₂e**, lo que indica una economía en expansión sin "
        f"desacoplamiento suficiente del carbono. Este crecimiento emisor implica que sus productos "
        f"de exportación tienen una **huella de carbono creciente**, haciéndolos más vulnerables a "
        f"mecanismos de ajuste fronterizo como el CBAM de la Unión Europea."
    )
elif variacion < 0:
    txt_comercial = (
        f"📉 **Impacto económico-comercial:** Desde 2015, las emisiones de {pais_sel} han "
        f"**disminuido en {abs(variacion):.0f} MtCO₂e**, señal de un desacoplamiento progresivo "
        f"entre crecimiento económico y emisiones. Sus exportaciones son menos vulnerables a "
        f"aranceles de carbono y podría incluso beneficiarse en mercados que premian productos "
        f"con baja huella de carbono."
    )
else:
    txt_comercial = (
        f"➡️ **Impacto económico-comercial:** Las emisiones de {pais_sel} se han mantenido "
        f"estables desde 2015, lo que sugiere estancamiento en la descarbonización."
    )

# Renderizar el análisis
col_info, col_gauge = st.columns([3, 1])

with col_info:
    st.markdown(f"### {emoji_estado} {pais_sel}")
    st.markdown(txt_brecha)
    st.markdown("---")
    st.markdown(f"#### 🌐 Riesgo diplomático y consecuencias")
    st.markdown(txt_riesgo)
    st.markdown("---")
    st.markdown(txt_comercial)

with col_gauge:
    st.markdown("#### Indicadores clave")
    st.metric("Brecha", f"{brecha:.1f}%",
              delta=f"{'↑ sobre meta' if brecha > 0 else '↓ bajo meta'}",
              delta_color="inverse")
    st.metric("Riesgo diplomático", f"{riesgo:.0f}/100")
    st.metric("Arancel estimado", f"{arancel:.1f}%")
    st.metric("Exportaciones a UE", f"{export_ue_val}%")

st.divider()

# ---------------------------------------------------------------
# GRÁFICAS ORIGINALES (mejoradas)
# ---------------------------------------------------------------
st.subheader("📊 Comparativa entre países")

tab1, tab2 = st.tabs(["Brecha de cumplimiento", "Riesgo vs. Arancel"])

with tab1:
    fig1 = px.bar(
        df.sort_values("brecha_pct"), x="brecha_pct", y="pais", orientation="h",
        color="estado", title="Brecha de cumplimiento (% sobre la trayectoria prometida)",
        color_discrete_map={"✅ Cumple": "#2e7d32", "⚠️ En riesgo": "#f9a825", "❌ Incumple": "#c62828"},
    )
    fig1.update_layout(height=400)
    st.plotly_chart(fig1, use_container_width=True)

with tab2:
    fig2 = px.scatter(
        df, x="arancel_pct", y="riesgo_diplomatico", size="actual_2023", color="estado",
        hover_name="pais", title="Consecuencias: arancel estimado vs. riesgo diplomático",
        labels={"arancel_pct": "Arancel de carbono estimado (%)", "riesgo_diplomatico": "Riesgo (0-100)"},
    )
    fig2.update_layout(height=450)
    st.plotly_chart(fig2, use_container_width=True)

# Tabla detallada
st.subheader("📋 Detalle por país")
st.dataframe(
    df[["pais", "estado", "brecha_pct", "proyeccion_2030", "meta_2030",
        "arancel_pct", "riesgo_diplomatico", "consecuencia"]].round(1),
    use_container_width=True, hide_index=True,
)
#se como funciona
with st.expander("¿Cómo se calcula?"):
    st.markdown(
        """
**Brecha de cumplimiento:**
- Se traza una línea recta entre las emisiones base (2015) y la meta prometida para 2030.
- Se calcula cuánto se desvía cada país de esa trayectoria lineal *hoy*.
- Si la brecha es **positiva**, el país emite más de lo que debería. Si es **negativa**, va mejor de lo prometido.

**Riesgo diplomático (0-100):**
- Combina dos factores:
  - **Brecha de emisiones** × 1.5: mientras mayor la brecha, mayor la presión internacional.
  - **Dependencia comercial** × 0.5: el % de exportaciones dirigidas a mercados con precio al carbono (ej. la UE con su CBAM).
- Se multiplica por el factor de **severidad diplomática** que eliges en la barra lateral.
- Un riesgo ≥60 implica posibles sanciones; entre 30 y 60, presión diplomática; bajo 30, riesgo bajo.

**Arancel de carbono estimado (%):**
- Simula un mecanismo tipo CBAM (Carbon Border Adjustment Mechanism).
- Crece con: la brecha del país, el precio internacional del carbono y la severidad diplomática.
- Es una heurística educativa, no una predicción exacta.

**Impacto comercial:**
- La variación de emisiones desde 2015 indica si el país ha desacoplado su economía del carbono.
- Un aumento implica mayor vulnerabilidad a aranceles fronterizos; una reducción, menor exposición.

Modelo simplificado con fines educativos; no es una predicción oficial.
        """
    )