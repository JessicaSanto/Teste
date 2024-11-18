import streamlit as st
import pandas as pd
import numpy as np

poi = pd.DataFrame({
    'lat': [37.77, 37.78, 37.79],
    'lon': [-122.41, -122.42, -122.43],
    'name': ['POI 1', 'POI 2', 'POI 3']
})

st.map(poi)



clientes = pd.DataFrame({
    'lat': [37.76, 37.75, 37.74],
    'lon': [-122.40, -122.39, -122.38],
    'cliente': ['Cliente 1', 'Cliente 2', 'Cliente 3']
})

st.map(clientes)


df = pd.DataFrame({
    "col1": np.random.randn(1000) / 50 + 37.76,
    "col2": np.random.randn(1000) / 50 + -122.4,
    "col3": np.random.randn(1000) * 100,
    "col4": np.random.rand(1000, 4).tolist(),
})

st.map(df, latitude='col1', longitude='col2', size='col3', color='col4')