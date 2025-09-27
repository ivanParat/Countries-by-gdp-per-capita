import streamlit as st
import pandas as pd
import numpy as np
import folium
import branca.colormap as bcm
from streamlit_folium import st_folium
import plotly.express as px
from lib import prepare_gdf, build_sidebar

st.set_page_config(layout="wide")
st.title("GDP per capita by country")
sidebar = build_sidebar(default_colors=["#D60000", "#FDE725", "#A8D200", "#11C800", "#008FC8", "#000DC8", "#9900C8"])  

gdp_type = sidebar['gdp_type']
gdf, year_columns, center = prepare_gdf(f"transformed_data/GDP_{gdp_type}_per_capita.geojson")

st.subheader("Map")
min_year = int(min(year_columns))
max_year = int(max(year_columns))
selected_year = st.slider("Select year", min_year, max_year, max_year, step=1, width=300)

st.write("Tip: hover a country for its name and GDP per capita. Missing values are grey.")

val_col = str(selected_year)
gdf["value"] = pd.to_numeric(gdf[val_col], errors="coerce").round(0)

if sidebar['colormap_scale'] == 'Absolute':
  vmin, vmax = float(gdf[year_columns].melt().value.min()), float(gdf[year_columns].melt().value.max())
else:
  vmin, vmax = min(gdf['value'].dropna()), max(gdf['value'].dropna())

colormap = bcm.LinearColormap(
    colors=sidebar['colormap_colors'],  
    vmin=vmin,
    vmax=vmax,
    caption=f"GDP per capita (USD) ({selected_year})"
)

m = folium.Map(location=center, zoom_start=2, tiles="CartoDB positron")

def style_function(feature):
    prop = feature.get("properties", {})
    v = prop.get("value", None)
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return {
            "fillColor": "#dddddd",
            "color": "#949494",
            "weight": 0.5,
            "fillOpacity": 0.4,
        }
    return {
        "fillColor": colormap(v),
        "color": "white",
        "weight": 0.5,
        "fillOpacity": 0.8,
    }

geojson = gdf.to_json()

folium.GeoJson(
    data=geojson,
    name="GDP per capita",
    style_function=style_function,
    tooltip=folium.GeoJsonTooltip(
        fields=["name_with_flag", "value"],
        aliases=["Country", f"GDP per capita (USD) ({selected_year})"],
        localize=True,
        sticky=False,
        labels=True,
        style=("background-color: white; color: #333333;"),
    ),
).add_to(m)

colormap.add_to(m)
folium.LayerControl().add_to(m)

st_folium(m, width=1000, height=650)

with st.expander(f"Top / Bottom countries (by GDP per capita) in {selected_year}", width=600):
    value_column = "GDP per capita (USD)"
    top = gdf.sort_values("value", ascending=False).head(10)[["name_with_flag","value"]].rename(columns={"name_with_flag": "Country", "value": value_column})
    bottom = gdf.sort_values("value", ascending=True).dropna(subset=["value"]).head(10)[["name_with_flag","value"]].rename(columns={"name_with_flag": "Country", "value": value_column})
    top[value_column] = top[value_column].apply(lambda x: f"{x:,.0f}")
    bottom[value_column] = bottom[value_column].apply(lambda x: f"{x:,.0f}")
    st.write("Top 10")
    st.dataframe(top, hide_index=True)
    st.write("Bottom 10 (non-null values)")
    st.dataframe(bottom, hide_index=True)

st.subheader("Line graph")

countries = [country for country in gdf['name'].tolist() if gdf.loc[gdf['name'] == country, year_columns].notna().any(axis=1).any()]

with st.container(width=500):
  selected_countries = st.multiselect("Select countries", countries, default=["United States of America", "China"])
  start_year = st.selectbox("Start year", year_columns, index=0, width=150)
  end_year = st.selectbox("End year", year_columns, index=len(year_columns)-1, width=150)

years = [y for y in year_columns if start_year <= y <= end_year]

df_plot = gdf[gdf["name"].isin(selected_countries)][["name"] + years]
df_long = df_plot.melt(id_vars="name", value_vars=years, var_name="Year", value_name="GDP per capita")
df_long["Year"] = df_long["Year"].astype(int)
df_long["GDP per capita"] = pd.to_numeric(df_long["GDP per capita"], errors="coerce").round(0)

fig = px.line(
    df_long,
    x="Year",
    y="GDP per capita",
    color="name",
    markers=True,
    labels={"name": "Country", "GDP per capita": "GDP per capita (USD)"},
    title="GDP per capita over time"
)

fig.update_layout(hovermode="x unified") 

st.plotly_chart(fig, use_container_width=True)