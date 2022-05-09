import streamlit as st
st.set_page_config(layout="wide")
import pandas as pd
import numpy as np
import altair as alt
import sys
import requests
import openpyxl
import plotly as plt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time

#### Functions
@st.cache(show_spinner=False)
def CGAC_list():
    url = 'https://github.com/abdelkaderalia/SpendApp/raw/main/Clean_Data/CGAC_list.xlsx'
    r = requests.get(url)
    data = r.content
    df = pd.read_excel(data)
    return df

@st.cache(show_spinner=False)
def historical(toptier_code):
    full = pd.DataFrame(columns=['fiscal_year','latest_action_date','toptier_code','transaction_count','obligations','messages'])
    for year in range(2008,2023):
        url = 'https://api.usaspending.gov'
        endpoint=f'/api/v2/agency/{toptier_code}/awards/'
        payload = {"fiscal_year":year}

        response = requests.get(f'{url}{endpoint}',params=payload)
        #print(response.status_code)
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data.items()).transpose()
            df.columns = df.iloc[0]
            df = df.tail(df.shape[0] -1)
            full = full.append(df)

    full['fiscal_year']=full['fiscal_year'].astype(str)
    full = full.rename(columns={"fiscal_year":"Fiscal Year","obligations":"Spending"})
    full = full.reset_index(drop=True)
    return full

@st.cache(show_spinner=False)
def category(toptier_code):
    full = pd.DataFrame(columns=['fiscal_year','name','abbreviation','total_obligations','transaction_count','new_award_count','children'])
    for year in range(2008,2023):
        url = 'https://api.usaspending.gov'
        endpoint=f'/api/v2/agency/{toptier_code}/sub_agency/'
        payload = {"fiscal_year":year}

        response = requests.get(f'{url}{endpoint}',params=payload)
        #print(response.status_code)
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data['results'])
            df.insert(loc = 0,column = 'fiscal_year',value = year)
            full = full.append(df)

    full = full.rename(columns={"name": "Subagency","fiscal_year":"Fiscal Year","total_obligations":"Spending"})
    full['Fiscal Year']=full['Fiscal Year'].astype(str)
    full = full.reset_index(drop=True)
    return full

@st.cache(show_spinner=False)
def breakdown_by(toptier_code):
    url = 'https://api.usaspending.gov'
    endpoint=f'/api/v2/agency/{toptier_code}/{breakdown}'
    payload = {"fiscal_year":2021}

    response = requests.get(f'{url}{endpoint}',params=payload)
    #print(response.status_code)
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data['results'])
        df = df.rename(columns={"name":"Breakdown","obligated_amount":"Spending"})
        return df

#### App starts here
if __name__ == "__main__":
    st.markdown('<h2 align="center">How much money does the federal government spend?</h2>', unsafe_allow_html=True)

    agencylist = CGAC_list()
    agencies = agencylist['AGENCY NAME'].tolist()

    agency_name = st.selectbox("Choose a federal agency:", agencies)
    code = agencylist.loc[agencylist['AGENCY NAME'] == agency_name, 'CGAC'].item()

    if agency_name != ' ':
        data_load_state = st.text('Loading data...')
        df_category_raw = category(code)
        c = df_category_raw.copy()

        if c.shape[0]==0:
            st.warning('Sorry, no data was found! Try a different agency.')
            data_load_state.empty()
        else:
            fig = px.bar(c, x="Fiscal Year", y="Spending", color="Subagency",title=f'{agency_name} Spending by Subagency',color_discrete_sequence=px.colors.qualitative.Prism)

            fig.update_xaxes(title_text="Fiscal Year")
            fig.update_yaxes(title_text="Spending ($)")
            fig.update_layout(height=700,font=dict(size=16),showlegend=False,title_x=0.5)
            #fig.update_layout(height=700,font=dict(size=16),legend=dict(yanchor="bottom",y=-0.45,xanchor="left",x=0,orientation="h"))

            st.plotly_chart(fig, use_container_width=True)

            data_load_state.text('Loading data...done!')
            time.sleep(1)
            data_load_state.empty()

            st.subheader(f'How does the {agency_name} compare to other agencies?')
            agency_name2 = st.selectbox("Choose another federal agency to compare:", agencies)

            if agency_name2 != ' ':
                code2 = agencylist.loc[agencylist['AGENCY NAME'] == agency_name2, 'CGAC'].item()
                if agency_name2 == agency_name:
                    st.warning('In order to compare, you have to choose a different agency!')
                else:
                    data_load_state = st.text('Loading data...')
                    counter = 1
                    for d in [code, code2]:
                        df_historical_raw = historical(d)
                        if counter==1:
                            a1 = df_historical_raw.copy()
                            a1.insert(loc = 1,column = 'Agency',value = agency_name)
                        elif counter==2:
                            a2 = df_historical_raw.copy()
                            a2.insert(loc = 1,column = 'Agency',value = agency_name2)
                        counter += 1

                    if a1.shape[0]==0 or a2.shape[0]==0:
                        st.warning('Sorry, no data was found! Choose a different agency to compare.')
                        data_load_state.empty()
                    else:
                        h = a1.append(a2)
                        fig = px.line(h, x='Fiscal Year', y='Spending', color='Agency',title=f'Compare Spending - {agency_name} and {agency_name2}',  color_discrete_sequence=px.colors.qualitative.G10)

                        fig.update_xaxes(title_text="Fiscal Year")
                        fig.update_yaxes(title_text="Spending ($)")
                        #fig.update_layout(height=600,font=dict(size=16))
                        fig.update_layout(height=600,font=dict(size=16),legend=dict(yanchor="bottom",y=-0.4,xanchor="center",x=0.5,orientation="h"),title_x=0.5)
                        fig.update_traces(line=dict(width=3))

                        st.plotly_chart(fig, use_container_width=True)

                        data_load_state.text('Loading data...done!')
                        time.sleep(1)
                        data_load_state.empty()

                        st.subheader(f'What did the {agency_name} spend money on 2021?')

                        select = st.radio("Breakdown spending by:",('Budget Function','Object Class'))

                        if select == 'Budget Function':
                            breakdown = 'budget_function/'
                        elif select == 'Object Class':
                            breakdown = 'object_class/'

                        data_load_state = st.text('Loading data...')
                        df_breakdown_raw = breakdown_by(code)
                        b = df_breakdown_raw.copy()

                        if b.shape[0]==0:
                            st.warning('Sorry, no data was found! Try another option.')
                            data_load_state.empty()
                        else:

                            fig = go.Figure(data=[go.Pie(labels=b['Breakdown'], values=b['Spending'])])
                            fig.update_traces(textfont_size=16,marker=dict(colors=px.colors.qualitative.Prism),rotation=140)
                            fig.update_layout(height=700,font=dict(size=16),showlegend=True,title=f'{agency_name} Spending Breakdown by {select}, 2021',title_x=0.5)
                            st.plotly_chart(fig, use_container_width=True)

                            data_load_state.text('Loading data...done!')
                            time.sleep(1)
                            data_load_state.empty()

                        st.subheader(f'What could we pay for with the {agency_name}\'s 2021 spending?')
                        st.text('(Based on estimates found online)')
                        #a1 = historical('097')
                        spend2021 = a1.loc[a1['Fiscal Year'] == '2021', 'Spending'].item()

                        st.markdown('<h4 align="center">Some costly (but important) expenditures</h4>', unsafe_allow_html=True)
                        col1, col2, col3 = st.columns(3)
                        num1 = col1.number_input('Clean water for everyone in the world - $10B',step=1)
                        num2 = col2.number_input('Deliver broadband internet to everyone in the U.S. - $80B',step=1)
                        num3 = col3.number_input('Resettle 1.2M Afghan refugees - $18.2B',step=1)

                        col1, col2, col3 = st.columns(3)
                        num4 = col1.number_input('End hunger in the U.S. - $25B',step=1)
                        num5 = col2.number_input('End homelessness in the U.S. - $20B',step=1)
                        num6 = col3.number_input('Pay off all outstanding U.S. private student loan debt - $131.1B',step=1)

                        st.markdown('<h4 align="center">Just for fun</h4>', unsafe_allow_html=True)
                        col1, col2, col3 = st.columns(3)
                        num7 = col1.number_input('Buy the Mona Lisa - $900M',step=1)
                        num8 = col2.number_input('Buy the Washington Wizards - $1.93B',step=1)
                        num9 = col3.number_input('Jeff Bezos\' net worth - $151.8B',step=1)

                        receipt = -(num1*10000000000) - (num2*80000000000) - (num3*18200000000) - (num4*25000000000) - (num5*20000000000) - (num6*131100000000) - (num7*900000000) - (num8*1930000000) - (num9*151800000000)

                        spend2021 = spend2021 + receipt

                        s = "{:,.2f}".format(spend2021)
                        receipt_output = "{:,.2f}".format(receipt)
                        spend_output = f'${s}'
                        col1, col2, col3, col4, col5 = st.columns(5)
                        budget = col3.metric(label="Left to spend", value=spend_output, delta=receipt_output)
