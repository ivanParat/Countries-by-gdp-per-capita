import streamlit as st
import pandas as pd
import numpy as np
import folium
import branca.colormap as bcm
from streamlit_folium import st_folium
import plotly.express as px
from lib import prepare_gdf, build_sidebar, attribution

st.set_page_config(layout="wide")
st.title("GDP per capita growth rate by country")
sidebar = build_sidebar(default_colors=["red", "white", "green"])  

gdp_type = sidebar['gdp_type']

gdf_growth_rate, year_columns, center = prepare_gdf(f"transformed_data/{gdp_type}_Growth_rate.geojson")
gdf_gdp_per_capita, year_columns, center = prepare_gdf(f"transformed_data/GDP_{gdp_type}_per_capita.geojson")

gdf = gdf_growth_rate

st.subheader("Map")

interval = st.radio(label='Choose single year or interval of multiple years' ,options=['Single year', 'Interval'])

min_year = int(min(year_columns))
max_year = int(max(year_columns))
if interval == "Single year":
    selected_year = st.slider("Select year", min_year, max_year, max_year, step=1, width=300)
    val_col = str(selected_year)
    gdf["value"] = pd.to_numeric(gdf[val_col], errors="coerce").round(2)
    start_year = selected_year - 1
    end_year = selected_year
else:
    start_year = st.selectbox("Start year", year_columns, index=0, width=150, key=0)
    end_year = st.selectbox("End year", year_columns, index=len(year_columns)-1, width=150, key=1)
    growth_type = st.radio(label='Choose absolute or annual growth' ,options=['Absolute', 'Annual'])
    gdf = gdf_gdp_per_capita
    valid_mask = gdf[start_year].notna() & gdf[end_year].notna() & (gdf[start_year] != 0)
    gdf['value'] = np.nan
    if growth_type == 'Absolute':
      gdf.loc[valid_mask, 'value'] = pd.to_numeric((gdf[end_year][valid_mask] / gdf[start_year][valid_mask] - 1) * 100.0).round(2)
    else:
      n = int(end_year) - int(start_year)
      if n <= 0:
        gdf['value'] = np.nan
      else:
        factor = gdf[end_year][valid_mask] / gdf[start_year][valid_mask]
        positive_mask = valid_mask & (factor > 0)
        gdf.loc[positive_mask, 'value'] = pd.to_numeric((factor[positive_mask] ** (1.0 / n) - 1) * 100).round(2)
        

st.write("Tip: hover a country for its name and GDP per capita growth rate. Missing values are grey.")

if sidebar['colormap_scale'] == 'Absolute':
  if interval == 'Interval':
     vmin, vmax = min(gdf['value'].dropna()), max(gdf['value'].dropna())
  else:
    vmin, vmax = float(gdf[year_columns].melt().value.min()), float(gdf[year_columns].melt().value.max())
else:
  vmin, vmax = min(gdf['value'].dropna()), max(gdf['value'].dropna())
limit = max(abs(vmin), abs(vmax))

colormap = bcm.LinearColormap(
    colors=sidebar['colormap_colors'],  
    vmin = - limit,
    vmax = limit,
    caption=f"GDP per capita growth rate ({start_year}-{end_year})"
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
        aliases=["Country", f"GDP per capita (USD) {growth_type.lower() if interval == 'Interval' else ""} growth rate % ({start_year}-{end_year})"],
        localize=True,
        sticky=False,
        labels=True,
        style=("background-color: white; color: #333333;"),
    ),
).add_to(m)

colormap.add_to(m)
folium.LayerControl().add_to(m)

st_folium(m, width=1000, height=650)

with st.expander(f"Top / Bottom countries (by GDP per capita growth rate) ({start_year}-{end_year})", width=600):
    value_column = f"GDP per capita (USD) {growth_type.lower() if interval == 'Interval' else ""} growth rate %"
    top = gdf.sort_values("value", ascending=False).head(10)[["name_with_flag","value"]].rename(columns={"name_with_flag": "Country", "value": value_column})
    bottom = gdf.sort_values("value", ascending=True).dropna(subset=["value"]).head(10)[["name_with_flag","value"]].rename(columns={"name_with_flag": "Country", "value": value_column})
    top[value_column] = top[value_column].apply(lambda x: f"{x:,.2f}")
    bottom[value_column] = bottom[value_column].apply(lambda x: f"{x:,.2f}")
    st.write("Top 10")
    st.dataframe(top, hide_index=True)
    st.write("Bottom 10 (non-null values)")
    st.dataframe(bottom, hide_index=True)

st.subheader("Line graph")

countries = [country for country in gdf['name'].tolist() if gdf.loc[gdf['name'] == country, year_columns].notna().any(axis=1).any()]

with st.container(width=500):
  selected_countries = st.multiselect("Select countries", countries, default=["United States of America", "China"])
  start_year_line_graph = st.selectbox("Start year", year_columns, index=0, width=150, key=3)
  end_year_line_graph = st.selectbox("End year", year_columns, index=len(year_columns)-1, width=150, key=4)

years = [y for y in year_columns if start_year_line_graph <= y <= end_year_line_graph]

gdf = gdf_growth_rate
df_plot = gdf[gdf["name"].isin(selected_countries)][["name"] + years]
df_long = df_plot.melt(id_vars="name", value_vars=years, var_name="Year", value_name="GDP per capita growth rate")
df_long["Year"] = df_long["Year"].astype(int)
df_long["GDP per capita growth rate"] = pd.to_numeric(df_long["GDP per capita growth rate"], errors="coerce").round(2)
max_val = df_long["GDP per capita growth rate"].abs().max()

fig = px.line(
    df_long,
    x="Year",
    y="GDP per capita growth rate",
    color="name",
    markers=True,
    labels={"name": "Country", "GDP per capita growth rate": "GDP per capita (USD) growth rate %"},
    title="GDP per capita growth rate over time"
)

fig.update_yaxes(range=[-max_val, max_val], zeroline=True, zerolinecolor="black")
fig.update_layout(hovermode="x unified") 

st.plotly_chart(fig, use_container_width=True)

attribution()