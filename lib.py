import streamlit as st
import re
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import geopandas as gpd

@st.cache_data
def prepare_gdf(filename, simplify_tolerance=0.05):
    gdf = gpd.read_file(filename)

    if simplify_tolerance is not None:
        gdf["geometry"] = gdf["geometry"].simplify(simplify_tolerance, preserve_topology=True)

    rep = gdf.geometry.representative_point()
    gdf["lon"] = rep.apply(lambda p: p.x)
    gdf["lat"] = rep.apply(lambda p: p.y)

    if gdf[["lat", "lon"]].dropna().empty:
        center = (0.0, 0.0)
    else:
        center = (float(gdf["lat"].mean()), float(gdf["lon"].mean()))

    year_cols = sorted([c for c in gdf.columns if isinstance(c, str) and c.isdigit() and len(c) == 4])

    return gdf, year_cols, center

HEX_RE = re.compile(r"^#([0-9A-Fa-f]{6})$")

def _parse_custom_colors(s):
    """Parse comma-separated color strings; accept hex (#rrggbb) or simple names like 'red'."""
    parts = [p.strip() for p in s.split(",") if p.strip()]
    clean = []
    for p in parts:
        if p.startswith("#"):
            if HEX_RE.match(p):
                clean.append(p)
            else:
                # invalid hex -> ignore
                continue
        else:
            # accept named colors (matplotlib/HTML names) — leave as-is
            clean.append(p)
    return clean


def _matplotlib_palette_to_hex(name, n=7):
    cmap = cm.get_cmap(name)
    colors = [mcolors.to_hex(cmap(i/(n-1))) for i in range(n)]
    return colors

mpl_names = cm._colormaps()
mpl_presets = {}
for name in mpl_names:
    pal = _matplotlib_palette_to_hex(name, n=7)
    if pal:
        display = name.capitalize() if name.islower() else name
        mpl_presets[display] = pal

def build_sidebar(default_colors, default_label="Default"):
    presets = {
        default_label: default_colors,
        "Custom": ""
    }
    presets.update(mpl_presets)

    with st.sidebar:
        st.header("Controls")

        gdp_type = st.radio("GDP measurement", ["Nominal", "PPP"])

        colormap = st.selectbox("Colormap", list(presets.keys()), index=0)

        custom_colors = None
        if colormap == "Custom":
            st.markdown(
                """
                Enter comma-separated colors (hex like `#RRGGBB` or color names).  
                **Hex example:** `#440154, #21918C, #FDE725`  
                **Color name example:** `red, white, green`
                """
            )
            txt = st.text_area("Colors", value=",".join(default_colors) if default_colors else "")
            cleaned = _parse_custom_colors(txt)
            if not cleaned:
                st.warning("No valid colors parsed from custom entry — falling back to default.")
            custom_colors = cleaned

        scale = st.radio("Colormap scale", ["By year", "Absolute"])

    if colormap == "Custom":
        final_colors = custom_colors if custom_colors else default_colors
    else:
        final_colors = presets.get(colormap, default_colors)

    return {"gdp_type": gdp_type, "colormap_name": colormap, "colormap_colors": final_colors, "colormap_scale": scale}

def attribution():
  return (
      st.markdown("<div style='height:200px'></div>", unsafe_allow_html=True),
      st.markdown(
            f"""
            **Data source:** World Bank — World Development Indicators (GDP per capita, nominal and PPP).  
            **Source pages:** World Bank Data (WDI).  
            **License:** Creative Commons Attribution 4.0 International (CC BY 4.0).  
            Link: https://data.worldbank.org · License: https://creativecommons.org/licenses/by/4.0/  
            (This app is independent and is not endorsed by the World Bank.)
            """,
            unsafe_allow_html=False
        )
  )
