import streamlit as st 
import pandas as pd 
import plotly.express as px

st.title ("Disease Dashboard")

data= pd.DataFrame({
  "year":[1999,2026]
  "cases":[100,200,300,400,500,600]
})

#graph
fig=px.line(data, x="year", y="cases", title="Disease Progression")
st.plotly_chart(fig)
