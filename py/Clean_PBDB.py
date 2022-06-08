import pandas as pd
import numpy as np
import sys
import requests

url = 'https://www.govinfo.gov/content/pkg/BUDGET-2023-DB/xls/BUDGET-2023-DB-1.xlsx' # Store link
r = requests.get(url) # Make request
open('temp.xlsx', 'wb').write(r.content) # Store results in a temporary file
df = pd.read_excel('temp.xlsx') # Read in as df
df