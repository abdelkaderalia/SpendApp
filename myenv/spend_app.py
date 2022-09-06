import streamlit as st
st.set_page_config(layout="wide") # Increase page width for app
import pandas as pd
import numpy as np
import asyncio
import aiohttp
import sys
import requests
import openpyxl
import plotly as plt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time


#### Functions

def human_format(num):
    """
    This function changes numbers to a human-interpretable SI format.
    Input: num (int)
    Output: Formatted number (string)
    """
    num = float('{:.3g}'.format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'),
                         ['', 'K', 'M', 'B', 'T'][magnitude])

@st.cache(show_spinner=False)
def CGAC_list():
    """
    This function imports the index of government agencies and corresponding Common Government Accounting Codes (CGAC) as a dataframe. Another script (Clean_CGAC.py) downloads the raw table of data and cleans it. The cleaned file is stored in the Github repository for this project, and this function loads the data from the raw Github link.
    Input: Github link (string)
    Output: Dataframe of agencies and CGAC codes (pd.Dataframe)
    """
    url = 'https://github.com/abdelkaderalia/SpendApp/raw/main/Clean_Data/CGAC_list.xlsx'
    r = requests.get(url)
    data = r.content
    df = pd.read_excel(data)
    s = pd.Series(df['CGAC'])
    df['CGAC']=pd.to_numeric(df['CGAC'],errors='coerce')
    df = df.fillna(0)
    df['CGAC']=df['CGAC'].apply(np.int64)
    df['CGAC']=df['CGAC'].astype(str)
    df['CGAC'] = np.where(df['CGAC'].apply(len)<3, df['CGAC'].str.zfill(3), df['CGAC'])
    df = df.iloc[1: , :]
    new_row = pd.DataFrame({'CGAC':' ', 'AGENCY NAME':' ','OTHER NAME':' ','Link':' ','Description':' ','Website':' '},index =[0])
    df = pd.concat([new_row, df]).reset_index(drop = True)
    return df


async def process_year(session,year,toptier_code,type):
    url = 'https://api.usaspending.gov'
    payload = {"fiscal_year":year}

    if type == 'historical':
        endpoint=f'/api/v2/agency/{toptier_code}/awards/'
        async with session.get(f'{url}{endpoint}',params=payload) as resp:
            data = await resp.json()
            df = pd.DataFrame(data.items()).transpose() # Convert to df and transpose
            df.columns = df.iloc[0] # Reset column names using first row
            df = df.tail(df.shape[0]-1) # Remove first row

    elif type == 'category':
        endpoint=f'/api/v2/agency/{toptier_code}/sub_agency/'
        async with session.get(f'{url}{endpoint}',params=payload) as resp:
            data = await resp.json()
            df = pd.DataFrame(data['results'])
            df.insert(loc = 0,column = 'fiscal_year',value = year)

    return df


async def async_func(toptier_code,type):
    async with aiohttp.ClientSession() as session:
        arr = []

        for year in range(2008,2023):
            df = process_year(session,year,toptier_code,type)
            arr.append(df)

        results = await asyncio.gather(*arr)

        if type == 'historical':
            full = pd.DataFrame(columns=['fiscal_year','toptier_code','transaction_count','obligations','messages','latest_action_date'])
            for item in results:
                full = full.append(item)

            full['fiscal_year']=full['fiscal_year'].astype(str) # Redefine year as string
            full = full.rename(columns={"fiscal_year":"Fiscal Year","obligations":"Spending"}) # Change column names
            full = full.reset_index(drop=True)

        elif type == 'category':
            full = pd.DataFrame(columns=['fiscal_year','name','abbreviation','total_obligations','transaction_count','new_award_count','children'])
            for item in results:
                full = full.append(item)

            full = full.rename(columns={"name": "Subagency","fiscal_year":"Fiscal Year","total_obligations":"Spending"}) # Rename columns
            full['Fiscal Year']=full['Fiscal Year'].astype(str) # Redefine year as string
            full = full.reset_index(drop=True)

        return full


@st.cache(show_spinner=False) # Use caching to improve speed and performance
def breakdown_by(toptier_code):
    """
    This function calls on the USASpending API to pull 2021 award data broken down by budget function or object class, depending on the user's input.
    Input: CGAC code (string)
    Output: Dataframe  results (pd.Dataframe)
    """
    # Set url, endpoint, and payload (params) for API call
    url = 'https://api.usaspending.gov'
    endpoint=f'/api/v2/agency/{toptier_code}/{breakdown}'
    payload = {"fiscal_year":2021}

    # API call
    response = requests.get(f'{url}{endpoint}',params=payload)
    # Check response
    if response.status_code == 200: # If successful
        data = response.json() # Store results
        df = pd.DataFrame(data['results']) # Convert to df
        df = df.rename(columns={"name":"Breakdown","obligated_amount":"Spending"}) # Rename columns
        return df


#### App starts here
if __name__ == "__main__":
    #st.markdown('<h2 align="left">How much money does the federal government spend?</h2>', unsafe_allow_html=True) # Add app title
    st.title('How much money does the federal government spend?')
    usasplink = 'https://www.usaspending.gov/'
    st.write(f'This app pulls live data directly from the Department of the Treasury\'s [USAspending database]({usasplink}) using their API. Their source for this data is the [Report on Budget Execution and Budgetary Resources](https://portal.max.gov/portal/document/SF133/Budget/FACTS%20II%20-%20SF%20133%20Report%20on%20Budget%20Execution%20and%20Budgetary%20Resources.html).')
    st.write(f'This data reflects an agency\'s obligated amounts, which are based on an agency\'s written commitments to use funds for a specific purpose. Check out the [Federal Spending Transparency Data Standards](https://portal.max.gov/portal/assets/public/offm/DataStandardsFinal.htm) to learn more about obligations and other terminology. Choose a federal agency below to explore their spending data.')
    st.subheader('')

    agencylist = CGAC_list() # Load CGAC list as df
    agencies = agencylist['AGENCY NAME'].tolist() # Convert agency names to list for dropdown menus

    agency_name = st.selectbox("Choose a federal agency:", agencies) # Store user selection for agency name

    if agency_name != ' ': # If agency name has been selected
        code = agencylist.loc[agencylist['AGENCY NAME'] == agency_name, 'CGAC'].item() # Store corresponding CGAC code for agency
        link = agencylist.loc[agencylist['AGENCY NAME'] == agency_name, 'Website'].item() # Store corresponding link for agency
        text = agencylist.loc[agencylist['AGENCY NAME'] == agency_name, 'Description'].item()

        if text != '':
            st.subheader(f'[{agency_name}]({link})')
            st.write(text)
        elif text == '':
            st.subheader(f'{agency_name}')

        data_load_state = st.text('Loading data...') # Show a message to indicate data is loading
        df = asyncio.run(async_func(code,'category'))

        if df.shape[0]==0: # If df of results had 0 rows
            st.warning('Sorry, no data was found! Try a different agency.') # Prompt the user to select another agency
            data_load_state.empty() # Clear warning message
        else: # If results are more than 0 rows
            if df.shape[0]<14:
                st.caption('*USAspending data for this agency is not available for all years.')
            elif df.shape[0]<=15:
                st.caption('*Detailed USAspending data is not available at the subagency level for this agency.')

            # Create segmented bar chart
            fig = px.bar(df, x="Fiscal Year", y="Spending", color="Subagency",title=f'{agency_name} - Spending by Subagency',color_discrete_sequence=px.colors.qualitative.Prism) # Create plot and set title and colors

            fig.update_xaxes(title_text="Fiscal Year") # Name x axis
            fig.update_yaxes(title_text="Spending ($)") # Name y axis
            fig.update_layout(height=700,font=dict(size=16),showlegend=False,title_x=0.5) # Set plot height, font size, hide legend, and center plot title
            #df['hoverdata'] = df['Spending'].apply(human_format)
            #fig.update_traces(customdata=df['hoverdata'],hovertemplate = "%{color} <br> %{customdata} </br><extra></extra>")

            st.plotly_chart(fig, use_container_width=True) # Show plot

            data_load_state.text('Loading data...done!') # Show messagge to indicate data has loaded
            time.sleep(1) # Wait one second
            data_load_state.empty() # Clear loading message

            st.subheader(f'How does the {agency_name} compare to other agencies?') # Add a subheader
            agency_name2 = st.selectbox("Choose another federal agency to compare:", agencies) # Store user selection for agency name 2

            if agency_name2 != ' ': # If agency name 2 has been selected
                code2 = agencylist.loc[agencylist['AGENCY NAME'] == agency_name2, 'CGAC'].item() # Store CGAC code for agency
                if agency_name2 == agency_name: # If agency name and agency 2 name are the same
                    st.warning('In order to compare, you have to choose a different agency!') # Prompt the user to select a different agency
                else:
                    data_load_state = st.text('Loading data...') # Show data loading message
                    counter = 1 # Set counter = 1
                    for d in [code, code2]: # For agency 1 and agency 2
                        if counter==1: # If counter = 1, store results for agency 1 and add column for name
                            a1 = asyncio.run(async_func(d,'historical')) # Run function to pull award data
                            a1.insert(loc = 1,column = 'Agency',value = agency_name)
                        elif counter==2: # If counter = 2, store results for agency 2 and add column for name
                            a2 = asyncio.run(async_func(d,'historical')) # Run function to pull award data
                            a2.insert(loc = 1,column = 'Agency',value = agency_name2)
                        counter += 1 # Add 1 to counter

                    if a1.shape[0]==0 or a2.shape[0]==0: # If results for agency 1 or agency 2 have 0 rows
                        st.warning('Sorry, no data was found! Choose a different agency to compare.') # Prompt the user to select another agency
                        data_load_state.empty() # Clear warning message
                    else: # If results have more than 0 rows
                        h = a1.append(a2) # Combine agency 1 and 2 results into df
                         # Create double line chart
                        fig = px.line(h, x='Fiscal Year', y='Spending', color='Agency',title=f'Compare Spending - {agency_name} and {agency_name2}',  color_discrete_sequence=px.colors.qualitative.G10) # Create plot, set title and colors

                        fig.update_xaxes(title_text="Fiscal Year") # Name x axis
                        fig.update_yaxes(title_text="Spending ($)") # Name y axis
                        fig.update_layout(height=600,font=dict(size=16),legend=dict(yanchor="bottom",y=-0.4,xanchor="center",x=0.5,orientation="h"),title_x=0.5) # Set plot height, font size, move legent to bottom center, center title
                        fig.update_traces(line=dict(width=3)) # Increase line thickness
                        fig.update_traces(mode="markers+lines", hovertemplate=None)
                        h['hoverdata'] = h['Spending'].apply(human_format)
                        fig.update_layout(hovermode="x")
                        #fig.update_traces(customdata = h['hoverdata'],hovertemplate = "%{customdata}")

                        #st.dataframe(h)
                        st.plotly_chart(fig, use_container_width=True) # Show plot

                        data_load_state.text('Loading data...done!') # Show message that data has loaded
                        time.sleep(1) # Wait for one second
                        data_load_state.empty() # Clear data load message

                        st.subheader(f'What did the {agency_name} spend money on 2021?') # Add another subheader

                        select = st.radio("Breakdown spending by:",('Budget Function','Object Class')) # Store user's selection of breakdown method from radio buttons

                        # Set end of API endpoint based on user selection
                        if select == 'Budget Function':
                            breakdown = 'budget_function/'
                        elif select == 'Object Class':
                            breakdown = 'object_class/'

                        data_load_state = st.text('Loading data...') # Show data loading message
                        df_breakdown_raw = breakdown_by(code) # Run function to pull breakdown data
                        b = df_breakdown_raw.copy() # Create a copy

                        if b.shape[0]==0: # If results have 0 rows
                            st.warning('Sorry, no data was found! Try another option.') # Prompt the user to select a different agency
                            data_load_state.empty() # Clear warning message
                        else: # If results have more than 0 rows

                            b['hoverdata'] = b['Spending'].apply(human_format)

                            # Create pie chart
                            fig = go.Figure(data=[go.Pie(labels=b['Breakdown'], values=b['Spending'])]) # Create plot
                            fig.update_traces(textfont_size=16,marker=dict(colors=px.colors.qualitative.Prism),rotation=140) # Set colors and font size, and rotate plot 140 degress so that slice labels don't overlap with plot title
                            fig.update_layout(height=700,font=dict(size=16),showlegend=True,title=f'{agency_name} - Spending Breakdown by {select}, 2021',title_x=0.5) # Set plot height, font size, title, and center title
                            fig.update_traces(customdata=b['hoverdata'],hovertemplate = "%{label} <br> %{percent} </br> %{customdata}<extra></extra>")
                            st.plotly_chart(fig, use_container_width=True) # Show plot

                            data_load_state.text('Loading data...done!') # Show message that data has loaded
                            time.sleep(1) # Wait one second
                            data_load_state.empty() # Clear data load message

                        st.subheader(f'What could we pay for with the {agency_name}\'s 2021 spending?') # Add another subheader
                        st.text('(Based on estimates found online)') # And some more text
                        spend2021 = a1.loc[a1['Fiscal Year'] == '2021', 'Spending'].item() # Store agency 1's 2021 spending amount from results of earlier function call (for line graph)

                        st.markdown('<h4 align="center">Some costly (but important) expenditures</h4>', unsafe_allow_html=True) # Add a subheader
                        # Create 3 columns for number widgets and put one st. number widget in each column
                        # Each widget has a title and also indicates that the user can enter integers on the interval of 1
                        # Store the value of the user's input
                        col1, col2, col3 = st.columns(3)
                        num1 = col1.number_input('Clean water for everyone in the world - $10B',step=1)
                        num2 = col2.number_input('Deliver broadband internet to everyone in the U.S. - $80B',step=1)
                        num3 = col3.number_input('Resettle 1.2M Afghan refugees - $18.2B',step=1)
                        # Create another row of 3 widgets
                        col1, col2, col3 = st.columns(3)
                        num4 = col1.number_input('End hunger in the U.S. - $25B',step=1)
                        num5 = col2.number_input('End homelessness in the U.S. - $20B',step=1)
                        num6 = col3.number_input('Pay off all outstanding U.S. private student debt - $131.1B',step=1)

                        st.markdown('<h4 align="center">Just for fun</h4>', unsafe_allow_html=True) # Add a subheader
                        # Create another row of 3 widgets
                        col1, col2, col3 = st.columns(3)
                        num7 = col1.number_input('Buy the Mona Lisa - $900M',step=1)
                        num8 = col2.number_input('Buy the Washington Wizards - $1.93B',step=1)
                        num9 = col3.number_input('Jeff Bezos\' net worth - $151.8B',step=1)

                        # Calculate the total 'spend' by the user based on their inputs and the 'price' of each item
                        receipt = -(num1*10000000000) - (num2*80000000000) - (num3*18200000000) - (num4*25000000000) - (num5*20000000000) - (num6*131100000000) - (num7*900000000) - (num8*1930000000) - (num9*151800000000)

                        spend2021 = spend2021 + receipt # Subtract the total 'spend' from agency 1's 2021 expenditures to calculate the balance

                        s = "{:,.2f}".format(spend2021) # Reformaat the balance with commas
                        receipt_output = "{:,.2f}".format(receipt) # Reformat the total 'spend' with commas
                        spend_output = f'${s}' # Show balance with a dollar sign
                        col1, col2, col3 = st.columns(3) # Create 5 columns
                        budget = col2.metric(label="Left to spend", value=spend_output, delta=receipt_output) # Show balance widget centered in column 3, and use receipt output to show the delta after each user selection
