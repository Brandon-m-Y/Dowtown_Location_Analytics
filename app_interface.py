# ── Imports ────────────────────────────────────────────────────────────────────
# pandas: Data manipulation and analysis - used for reading CSV files and data processing
import pandas as pd
# streamlit: Web app framework - used to create the interactive dashboard interface
import streamlit as st
# pydeck: 3D geospatial visualization library - used to create interactive maps
import pydeck as pdk      
# altair: Declarative statistical visualization library - used for creating scatter plots with trendlines
import altair as alt

# ── Configuration ────────────────────────────────────────────────────────────
# Dictionary mapping city names (as they appear in the UI) to their corresponding CSV data files
# Each CSV file contains restaurant/business data scraped from Google Places API for that city
CITY_FILES = {
    'Hamilton, OH': 'data/places_restaurants_hamiltonOH.csv',
    'Cincinnati, OH': 'data/places_restaurants_CincinnatiOH.csv',
    'Westchester, OH': 'data/places_restaurants_WestchesterOH.csv'
}

@st.cache_data
def load_city_data(city_option):
    file_path = CITY_FILES.get(city_option)
    if not file_path:
        st.error("Invalid city selection")
        return pd.DataFrame()
    
    df = pd.read_csv(file_path)
    
    # Rename the Google Places nested columns → standard names
    if 'geometry.location.lat' in df.columns and 'geometry.location.lng' in df.columns:
        df = df.rename(columns={
            'geometry.location.lat': 'lat',
            'geometry.location.lng': 'lon'
        })
    else:
        st.warning("Expected Google Places columns not found — map may not work.")
    
    return df

# ── Main App ───────────────────────────────────────────────────────────────
st.title('Downtown Business Explorer')

option = st.selectbox(
    '##### Choose Your City',
    list(CITY_FILES.keys())
)

df = load_city_data(option)

if df.empty:
    st.stop()

# Safety check for required map columns
if 'lat' not in df.columns or 'lon' not in df.columns:
    st.error("No 'lat' / 'lon' columns after renaming. Check your CSV structure.")
    st.dataframe(df.head())  # debug help
    st.stop()


# Prepare data for the map
map_df = df[['lat', 'lon', 'name', 'rating', 'distance_to_downtown_km', 'international_phone_number']].copy()

# Drop rows missing required coordinates
map_df = map_df.dropna(subset=['lat', 'lon'])



# ── IMPORTANT: Pre-format numbers as strings for tooltip ───────────────────
map_df['distance_formatted'] = map_df['distance_to_downtown_km'].map('{:.2f}'.format)
map_df['rating_formatted']   = map_df['rating'].map('{:.1f}'.format)  # optional, 1 decimal for rating

if map_df.empty:
    st.info("No valid location data available for this city.")
else:
    # Center view
    view_state = pdk.ViewState(
        latitude=map_df["lat"].mean(),
        longitude=map_df["lon"].mean(),
        zoom=12,
        pitch=0
    )

    layer = pdk.Layer(
        'ScatterplotLayer',
        data=map_df,
        get_position='[lon, lat]',
        get_radius=50,
        get_fill_color=[255, 80, 80, 180],
        pickable=True
    )

    # Now use the pre-formatted columns in tooltip
    tooltip = {
        "html": """
            <b>{name}</b><br>
            Rating: {rating_formatted} ★<br>
            Distance: {distance_formatted} km<br>
            Phone: {international_phone_number}
        """,
        "style": {
            "backgroundColor": "white",
            "color": "black",
            "fontFamily": "Arial",
            "padding": "8px",
            "borderRadius": "4px",
            "boxShadow": "2px 2px 8px rgba(0,0,0,0.25)"
        }
    }

    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style='mapbox://styles/mapbox/light-v9'
    )

    st.pydeck_chart(deck, use_container_width=True)

# ── The rest stays the same ────────────────────────────────────────────────

# Optional preview/debug
with st.expander("Show first 15 rows of data ordered by highest rating"):
    df1 = df[['name','international_phone_number','rating', 'distance_to_downtown_km']] \
          .sort_values(by='rating', ascending=False) \
          .head(15)
    st.dataframe(df1)

# Optional: show some data preview
with st.expander("Preview first 100 rows"):
    df2 = df[['name','international_phone_number','rating', 'distance_to_downtown_km']]
    st.dataframe(df2.head(100))

# Show Scatterplot of rating vs distance to downtown with a trendline
with st.expander("Rating vs Distance — Detailed View"):
    if all(col in df.columns for col in ['distance_to_downtown_km', 'rating', 'name']):
        chart_data = df[['name', 'distance_to_downtown_km', 'rating']].dropna()
        
        base = alt.Chart(chart_data).mark_circle(
            size=100, opacity=0.7
        ).encode(
            x=alt.X('distance_to_downtown_km:Q', title='Distance to Downtown (km)'),
            y=alt.Y('rating:Q', title='Google Rating', scale=alt.Scale(domain=[1, 5])),
            tooltip=['name', 'rating', 'distance_to_downtown_km']
        )
        
        trend = base.transform_regression(
            'distance_to_downtown_km', 'rating'
        ).mark_line(color='red', opacity=0.6)
        
        full_chart = (base + trend).properties(
            width=700,
            height=450,
            title=f"{option} — Rating vs Distance to Downtown"
        ).interactive()
        
        st.altair_chart(full_chart, use_container_width=True)
    else:
        st.info("Need 'name', 'rating' and 'distance_to_downtown_km' columns for detailed chart.")