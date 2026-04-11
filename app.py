import streamlit as st 
import pandas as pd 
import plotly.express as px
import requests

st.set_page_config(page_title="Disease Dashboard", layout="wide")

st.title ("Disease and Genetic Risk Dashboard")

#load WHO data
@st.cache_data
def load_who_data():
  url = "https://ghoapi.azureedge.net/api/IndicatorData"
  response= requests.get(url)
  df= pd.DataFrame(response.json()["value"])
  #keep only useful columns 
  df = df[["SpatialDim","TimeDim","NumericValue","Indicator"]]

  #Rename
  df = df.rename(columns={
    "SpatialDim": "Country",
    "TimeDim": "Year",
    "NumericValue": "Cases",
    "Indicator":"Disease"
  })

  #Clean
  df=df.dropna(subset=["Cases","Year"])

  return df 
#LOAD CDC DATA 
@st.cache_data():
def load_cdc_data():
  url = "https://data.cdc.gov/resource/9mfq-cb36.json"
  try:
    df = pd.read_json(url)
    
    df=df.rename(columns={
      "year":"Year",
      "data_value": "Cases",
      "locationabbr": "Country"
    })

    #Convert state abbreviations to USA label
    df["Country"]="USA"

    #Add disease label (CDC dataset is usually one disease)
    df["Disease"] = "CDC Reported Disease"
    
    df = df.dropna(subset=["Cases","Year"])

  except:
    df=pd.DataFrame()

  return df

#LOAD COUNTRY CODES
@st.cache_data
def load_country_codes():
  return pd.read_csv(
    "https://raw.githubusercontent.com/plotly/datasets/master/2014_world_gdp_with_codes.csv"
  )[["COUNTRY","CODE"]].rename(columns={
      "COUNTRY": "CountryName",
      "CODE": "ISO3"
  })

#LOAD GWAS DATA(REAL API)

@st.cache_data
def load_gwas_data():
  url = "https://www.ebi.ac.uk/gwas/rest/api/associations"
  response = requests.get(url)
  data= response.json()

  records= []

  for item in data["_embedded"]["associations"][:300]: #limit for speed
    trait=item.get("trait","Unknown")
    snp = item.get("variantID","Unknown")
    pval = item.get("pvalue", None)

    records.append({
      "Trait":trait,
      "SNP":snp,
      "PValue":pval
    })
  return pd.DataFrame(records)

#LOAD DATA
who=load_who_data()
cdc=load_cdc_data()
codes= load_country_codes()
gwas=load_gwas_data()

#Combine WHO + CDC
data = pd.concat([who,cdc],ignore_index=True)

#sidebar filters
st.sidebar.header("Filters")

diseases= data ["Disease"].dropna().unique()[:50]

selected_disease=st.sidebar.multiselect(
  "Select Disease(s)", 
  diseases,
  default=diseases[:2]
)

year_list= sorted(data["Year"].dropna(),unique())
selected_year=st.sidebar.selectbox("Select Year", year_list)

mutation = st.sidebar.selectbox(
  "Select SNP (GWAS)",
  gwas["SNP"].dropna().unique()[:100]
)

#FILTER DATA 
filtered = data[
  (data["Disease"].isin(selected_diseases))&
  (data["Year"]==selected_year)
]
trend= data[data["Disease"].isin(selected_diseases)]

#DISEASE TREND

st.subheader("Disease Progression")

fig= px.line(
  trend,
  x="Year",
  y="Cases",
  title="Disease Progression Over Time"
)

st.plotly_chart(fig, use_container_width=True)

#Global Map

st.subheader("Global Disease Map")

map_df=filtered.groupby("Country", as_index=False)["Cases"].mean()

map_df = map_df.merge(
  codes,
  left_on="Country",
  right_on="CountryName",
  how="left"
)

fig_map=px.choropleth(
  map_df,
  locations="ISO3",
  color="Cases",
  color_continuous_scale="Reds",
  title="Disease Prevalence by Country"
)

st.plotly_chart(fig_map, use_container_width=True)

#GWAS ANALYSIS
st.subheader("GWAS-Based Risk Analysis")

select_gwas= gwas[gwas["SNP"]==mutation]

if not selected_gwas.empty:
  trait = selected_gwas.iloc[0]["Trait"]

  st.write(f"### SNP:{mutation}")
  st.write(f"Associated Trait: **{trait}**")

  matched= [d for d in selected_diseases if trait in d.lower()]

  if matched:
    st.success(f"Matched Disease(s): {matched}")

  risk_data = data[
    (data["Disease"].isin(matched)) &
    (data["Year"]== selected_year)
  ]

  high_risk = risk_data[
    risk_data["Cases"] > risk_data["Cases"].quantile(0.75)
  ]
  regions = high_risk["Country"].unique()
  
  st.warning ("High-risk regions based on disease prevalence:")
  st.write(list(regions))

  st.info("Recommendation: Avoid or take precautions in these areas.")

else:
  st.write("No strong match between SNP and selected diseases.")

#BAR CHART
st.subheader("Top Countries")
top=map_df.sort_values(by="Cases", ascending=False).head(10)

fig_bar=px.bar(top,x="Country", y="cases")

st.plotly_chart(fig_bar, use_container_width=True)

#RAW DATA
with st.expander("View Data"):
  st.dataframe(filtered)
 
