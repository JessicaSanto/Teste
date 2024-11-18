import streamlit as st
import pandas as pd
import pydeck as pdk

# Criação do DataFrame com umidade
clientes = pd.DataFrame({
    'lat': [37.76, 37.75, 37.74],
    'lon': [-122.40, -122.39, -122.38],
    'cliente': ['Cliente 1', 'Cliente 2', 'Cliente 3'],
    'umidade': [60, 65, 70]  # Adicionando dados de umidade
})

# Configuração do mapa com pydeck para mostrar a umidade
layer = pdk.Layer(
    'ScatterplotLayer',
    data=clientes,
    get_position='[lon, lat]',
    get_color='[200, 30, 0, 160]',
    get_radius=200,
    pickable=True
)

# Configuração da visualização do mapa e tooltip para exibir a umidade
view_state = pdk.ViewState(
    latitude=37.75,
    longitude=-122.39,
    zoom=12,
    pitch=50,
)

# Tooltip para mostrar a umidade quando o ponto é selecionado
tooltip = {
    "html": "<b>Cliente:</b> {cliente} <br/> <b>Umidade:</b> {umidade}%",
    "style": {"color": "white"}
}

# Mapa interativo
st.pydeck_chart(pdk.Deck(
    layers=[layer],
    initial_view_state=view_state,
    tooltip=tooltip
))