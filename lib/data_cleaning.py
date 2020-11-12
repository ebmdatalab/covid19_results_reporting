import pandas as pd
from datetime import date
import re
import unicodedata
import text_unidecode as unidecode

def enrollment_dates(x):
    format_1 = re.compile(r"\d{4}/\d{2}/\d{2}")
    format_2 = re.compile(r"\d{2}/\d{2}/\d{4}")
    format_3 = re.compile(r"\d{4}-\d{2}-\d{2}")
    format_4 = re.compile(r"\d{2}-\d{2}-\d{4}")
    if isinstance(x, str) and x[0].isalpha():
        return pd.to_datetime(x)
    elif isinstance(x, str) and bool(re.match(format_1, x)):
        return pd.to_datetime(x, format='%d/%m/%Y')
    elif isinstance(x, str) and bool(re.match(format_2, x)):
        return pd.to_datetime(x, format='%Y/%m/%d')
    elif isinstance(x, str) and bool(re.match(format_3, x)):
        return pd.to_datetime(x, format='%Y-%m-%d')
    elif isinstance(x, str) and bool(re.match(format_4, x)):
        return pd.to_datetime(x, format='%d-%m-%Y')
    else:
        return pd.to_datetime(x, errors='coerce')


def fix_date(x):
    if isinstance(x,str):
        return x
    else:
        x = pd.to_datetime(x).date()
        return x

def fix_errors(fix_dict, df):
    for a, b in fix_dict.items():
        if a in df.TrialID.tolist():
            ind = df[df.TrialID == a].index.values[0]
            if str(df.at[ind, 'Date enrollement']) == str(b[0]):
                df.at[ind, 'Date enrollement'] = b[1]
            else:
                print(f'Original Value Did not Match for {a}')
    return df
    
def d_c(x):
    return x[x.TrialID.duplicated()]

def enroll_extract(e_list):
    extracted_size = []
    for s in e_list:
        try:
            s = int(s)
            extracted_size.append(s)
        except (ValueError, TypeError):
            if not s or pd.isnull(s):
                extracted_size.append('Not Available')
            elif isinstance(s,str):
                digits = []
                nums = re.findall(r':\d{1,10};',s)
                for n in nums:
                    digits.append(int(n.replace(':','').replace(';','')))
                extracted_size.append(sum(digits))
            else:
                print(f'Unsupported Type: {type(s)}')
                raise 
    return extracted_size

def norm_names(x):
    if isinstance(x,float):
        return x
    else:
        text = unidecode.unidecode(x)
        normed = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode()
        return normed 