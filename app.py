import streamlit as st 
import pandas as pd 
import plotly.express as px

st.set_page_config(page_title="Disease Dashboard", layout="wide")

st.title ("Disease and Genetic Risk Dashboard")

#fallback data 
fallback=pd.DataFrame({
  "Country":["USA","India","Brazil","UK","Germany","China"],
  "Year":[2000,2005,2010,2015,2020,2022],
  "Cases":[120,300,500,700,650,900],
  "Disease":["cancer","diabetes","tuberculosis","hiv","malaria","cardiovascular"]
})

#load WHO data
@st.cache_data
def load_who_data():
  try:
    df = pd.read_excel("who.xlsx")

    #Normalize column names
    df.columns = df.columns.str.strip().str.lower()

    #Debug: see columns
    st.write("WHO columns:", df.columns.tolist())

    #Rename
    df = df.rename(columns={
      "location": "Country",
      "parentlocation":"Continent",
      "period": "Year",
      "indicator":"Disease",
      "factvaluenumeric": "Cases",
    })

    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df["Cases"]=pd.to_numeric(df["Cases"],errors="coerce")

    df= df[["Country","Year","Cases","Disease"]]
    
    df=df.dropna()
    
    return df 
    
  except Exception as e:
    st.write("WHO ERROR:", e)
    return fallback 

  
#LOAD CDC DATA 
@st.cache_data
def load_cdc_data():
  try:
    df = pd.read_excel("cdc.csv.xlsx", engine="openpyxl")

    #Debug
    st.write("CDC columns:", df.columns.tolist())
    
    df=df.rename(columns={
      "YearEnd": "Year",
      "LocationDesc": "Country",
      "DataValueAlt":"Cases",
      "Topic":"Disease"
    })

    #Convert state abbreviations to USA label
    df["Country"]="USA"

    #Add disease label (CDC dataset is usually one disease)
    df["Disease"] = "CDC Reported Disease"

    df["Year"]= pd.to_numeric(df["Year"], errors="coerce")
    df["Cases"]=pd.to_numeric(df["Cases"], errors="coerce")
    
    df = df.dropna(subset=["Year","Cases"])

    #Aggregate to yearly USA total
    df=df.groupby("Year", as_index=False)["Cases"].sum()
    
    df["Country"]="USA"
    df["Disease"]="CDC Reported Disease"

    return df

  except Exception as e:
    st.write("CDC ERROR:", e)
    return pd.DataFrame() 

#LOAD COUNTRY CODES
@st.cache_data
def load_country_codes():
    url = "https://raw.githubusercontent.com/plotly/datasets/master/2014_world_gdp_with_codes.csv"
    df= pd.read_csv(url)

    df=df.rename(columns={
        "COUNTRY": "Country",
        "CODE": "ISO3"
    })
    return df

#LOAD GWAS DATA
@st.cache_data
def load_gwas_data():
  try:
    df = pd.read_csv("gwas.csv")

    df["Trait"]=df["Trait"].str.lower()

    return df

  except Exception as e:
    st.write("GWAS ERROR:", e)
    return pd.DataFrame({
      "Trait": ["cancer","diabetes"],
      "SNP":["rs1","rs2"]
    })

#LOAD DATA
who=load_who_data()
cdc=load_cdc_data()
codes= load_country_codes()
gwas=load_gwas_data()

#Combine WHO + CDC
data = pd.concat([who,cdc],ignore_index=True)

#if everything fails 
if data.empty:
  data= fallback

#DEBUG(REMOVE LATER) 
st.write("WHO DATA SAMPLE", who.head())
st.write("GWAS DATA SAMPLE",gwas.head())

#sidebar filters
st.sidebar.header("Filters")

diseases= sorted(data["Disease"].unique())

selected_diseases=st.sidebar.multiselect(
  "Select Disease(s)", 
  diseases,
  default=diseases[:3]
)

countries = sorted(data["Country"].unique())
selected_countries = st.sidebar.multiselect(
  "Selected Countries",
  countries, 
  default = countries [:5]
)

year_list= sorted(data["Year"].dropna().unique())
selected_year=st.sidebar.selectbox("Select Year", year_list)

mutation = st.sidebar.selectbox(
  "Select SNP (GWAS)",
  gwas["SNP"].dropna().unique()
)

#FILTER DATA 
filtered = data[
  (data["Disease"].isin(selected_diseases))&
  (data["Country"].isin(selected_countries))&
  (data["Year"]==selected_year)
]
trend= data[
  (data["Disease"].isin(selected_diseases)) &
  (data["Country"].isin(selected_countries))
]

#DISEASE TREND

st.subheader("Disease Progression")

fig= px.line(
  trend,
  x="Year",
  y="Cases",
  color="Disease",
  line_group="Country",
  title="Disease Progression Over Time"
)

st.plotly_chart(fig, use_container_width=True)

#Global Map

st.subheader("Global Disease Map")

map_df=filtered.groupby("Country", as_index=False)["Cases"].mean()

map_df = map_df.merge(
  codes,
  on="Country",
  how="left"
)

fig_map=px.choropleth(
  map_df,
  locations="ISO3",
  color="Cases",
  hover_name="Country",
  color_continuous_scale="Reds",
  title="Disease Prevalence by Country"
)

st.plotly_chart(fig_map, use_container_width=True)

#GWAS ANALYSIS
st.subheader("GWAS-Based Risk Analysis")

selected_gwas= gwas[gwas["SNP"]==mutation]

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

    st.info(
      "Recommendation: Individuals with this mutation should "
      "avoid or take precautions in these regions."
    )

  else:
    st.write("No strong match between SNP and selected diseases.")

#BAR CHART
st.subheader("Top Countries")
top=map_df.sort_values(by="Cases", ascending=False).head(10)

fig_bar=px.bar(top,x="Country", y="Cases")

st.plotly_chart(fig_bar, use_container_width=True)

#RAW DATA
with st.expander("View Data"):
  st.dataframe(filtered)
 
