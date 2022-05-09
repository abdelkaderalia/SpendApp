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
def CGAC_list(url):
    r = requests.get(url)
    open('temp.xlsx', 'wb').write(r.content)
    df = pd.read_excel('temp.xlsx')
    df = df.iloc[3:,1:3]
    df.columns = df.iloc[0]
    df = df.tail(df.shape[0] -1)
    df['AGENCY NAME']=df['AGENCY NAME'].str.title()

    to_replace = ['The Judicial Branch','The Legislative Branch','Agriculture, Department Of (1200)','Commerce, Department Of (1300)','Interior, Department Of The (1400)','Justice, Department Of (1500)','Labor, Department Of (1600)','State, Department Of (1900)','Treasury, Department Of The (2000)','Office Of Personnel Management (2400)','Social Security Administration (2800)','Nuclear Regulatory Commission (3100)','General Services Administration (4700)','National Science Foundation (4900)','Environmental Protection Agency (6800)','Homeland Security, Department Of (7000)','Agency For International Development (1152)','Small Business Administration (7300)','Health And Human Services, Department Of (7500)','National Aeronautics And Space Administration (8000)','Housing And Urban Development, Department Of (8600)','Energy, Department Of (8900)','Education, Department Of (9100)','Veterans Affairs, Department Of 3600)','Transportation, Department Of']

    replace_values = ['Judicial Branch','Legislative Branch','Department of Agriculture','Department of Commerce','Department of the Interior','Department of Justice','Department of Labor','Department of State','Department of the Treasury','Office of Personnel Management','Social Security Administration','Nuclear Regulatory Commission','General Services Administration','National Science Foundation','Environmental Protection Agency','Department of Homeland Security','Agency for International Development','Small Business Administration','Department of Health and Human Services','National Aeronautics and Space Administration','Department of Housing and Urban Development','Department of Energy','Department of Education','Department of Veterans Affairs','Department of Transportation']

    df = df.replace(to_replace,replace_values)
    df['AGENCY NAME'] = df['AGENCY NAME'].str.replace('Of','of')
    df['AGENCY NAME'] = df['AGENCY NAME'].str.replace('On','on')
    df['AGENCY NAME'] = df['AGENCY NAME'].str.replace('Or','or')
    df['AGENCY NAME'] = df['AGENCY NAME'].str.replace('organization','Organization')
    df['AGENCY NAME'] = df['AGENCY NAME'].str.replace('For','for')
    df['AGENCY NAME'] = df['AGENCY NAME'].str.replace('The','the')
    df['AGENCY NAME'] = df['AGENCY NAME'].str.replace('And','and')
    df['AGENCY NAME'] = df['AGENCY NAME'].str.replace('office','Office')
    new_row = pd.DataFrame({'CGAC':'097', 'AGENCY NAME':'Department of Defense'},index =[0])
    df = pd.concat([new_row, df]).reset_index(drop = True)
    df = df.drop_duplicates(subset=['AGENCY NAME'])
    df = df.sort_values(by=['AGENCY NAME'])
    new_row = pd.DataFrame({'CGAC':' ', 'AGENCY NAME':' '},index =[0])
    df = pd.concat([new_row, df]).reset_index(drop = True)

    return df

@st.cache(show_spinner=False)
def historical(toptier_code):
    full = pd.DataFrame(columns=['fiscal_year','latest_action_date','toptier_code','transaction_count','obligations','messages'])
    for year in range(2008,2021):
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

#dodhistorical = historical('097')
#dodhistorical.to_excel('/Users/Alia/Documents/Github/SpendApp/Clean_Data/dodhistorical.xlsx',index = False, header=True)

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

#dodsubagency = category('097')
#dodsubagency.to_excel('/Users/Alia/Documents/Github/SpendApp/Clean_Data/dodsubagency.xlsx',index = False, header=True)

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

#dodbreakdown = breakdown('097')
#dodbreakdown.to_excel('/Users/Alia/Documents/Github/SpendApp/Clean_Data/dodbreakdown.xlsx',index = False, header=True)

if __name__ == "__main__":
    st.markdown('<h2 align="center">How much money does the federal government spend?</h2>', unsafe_allow_html=True)

    agencylist = CGAC_list('https://www.dla.mil/Portals/104/Documents/DLMS/Committees/DoDAAD/CGAC-Table-for-DoDAAD.xlsx')
    agencies = agencylist['AGENCY NAME'].tolist()

    agency_name = st.selectbox("Choose a federal agency:", agencies)
    code = agencylist.loc[agencylist['AGENCY NAME'] == agency_name, 'CGAC'].item()

    if agency_name != ' ':
        data_load_state = st.text('Loading data...')
        df_category_raw = category(code)
        c = df_category_raw.copy()

        if c.shape[0]==0:
            st.warning('Sorry, no data was found! Try a different agency.')
        else:
            fig = px.bar(c, x="Fiscal Year", y="Spending", color="Subagency",title=f'{agency_name} Spending by Subagency',color_discrete_sequence=px.colors.qualitative.Prism)

            fig.update_xaxes(title_text="Fiscal Year")
            fig.update_yaxes(title_text="Spending ($)")
            fig.update_layout(height=600,font=dict(size=16),showlegend=False,title_x=0.5)
            #fig.update_layout(height=700,font=dict(size=16),legend=dict(yanchor="bottom",y=-0.45,xanchor="left",x=0,orientation="h"))

            st.plotly_chart(fig, use_container_width=True)

            data_load_state.text('Loading data...done!')
            time.sleep(1)
            data_load_state.empty()

            agency_name2 = st.selectbox("Choose another federal agency to compare:", agencies)

            if agency_name2 != ' ':
                code2 = agencylist.loc[agencylist['AGENCY NAME'] == agency_name2, 'CGAC'].item()
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
                    st.warning('Sorry, no data was found! Try a different agency.')
                else:
                    h = a1.append(a2)
                    fig = px.line(h, x='Fiscal Year', y='Spending', color='Agency',title=f'Compare Spending - {agency_name} and {agency_name2}',  color_discrete_sequence=px.colors.qualitative.G10)

                    fig.update_xaxes(title_text="Fiscal Year")
                    fig.update_yaxes(title_text="Spending ($)")
                    #fig.update_layout(height=600,font=dict(size=16))
                    fig.update_layout(height=500,font=dict(size=16),legend=dict(yanchor="bottom",y=-0.4,xanchor="center",x=0.5,orientation="h"),title_x=0.5)
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
                    else:
                        fig = px.pie(b, values='Spending', names='Breakdown',title=f'{agency_name} Spending Breakdown by {select}',color_discrete_sequence=px.colors.qualitative.Prism)

                        fig.update_layout(height=700,font=dict(size=16),showlegend=True,title_x=0.5,margin=dict(t=150))
                        #fig.update_layout(height=700,font=dict(size=16),legend=dict(yanchor="bottom",y=-0.45,xanchor="left",x=0,orientation="h"))

                        st.plotly_chart(fig, use_container_width=True)

                        data_load_state.text('Loading data...done!')
                        time.sleep(1)
                        data_load_state.empty()

                    #st.subheader(f'What could we buy with the {agency_name}\'s 2021 contract expenditures?')
