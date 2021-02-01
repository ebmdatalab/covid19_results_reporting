# -*- coding: utf-8 -*-
# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: all
#     notebook_metadata_filter: all,-language_info
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.3.3
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# This notebook takes the raw ICTRP COVID-19 registered trials CSV, cuts it down to only the fields we need, and cleans/processes the data using techniques developed for covid19.trialstracker.net

# +
import sys
from pathlib import Path
import os
cwd = os.getcwd()
parent = str(Path(cwd).parents[0])
sys.path.append(parent)

# %load_ext autoreload
# %autoreload 2
# -

import pandas as pd
import numpy as np
from datetime import date

df = pd.read_csv(parent + '/data/ictrp_data/COVID19-web_29June2020.csv', dtype={'Phase': str})

# +
from lib.data_cleaning import enrollment_dates, fix_date, fix_errors, d_c

#This is fixes for known broken enrollement dates    
known_errors= {
    'IRCT20200310046736N1': ['2641-06-14', '2020-04-01'],
    'EUCTR2020-001909-22-FR': ['nan', '2020-04-29']
}
# -

df = fix_errors(known_errors, df)

# +
df['Date enrollement'] = df['Date enrollement'].apply(enrollment_dates)

df['Date registration'] = pd.to_datetime(df['Date registration3'], format='%Y%m%d')

# +
from lib.data_cleaning import enroll_extract

#Extracting target enrollment
size = df['Target size'].tolist()

df['target_enrollment'] = enroll_extract(size)

#Creating retrospective registration
df['retrospective_registration'] = np.where(df['Date registration'] > df['Date enrollement'], True, False)

# +
#Taking only what we need right now

cols = ['TrialID', 'Source Register', 'Date registration', 'Date enrollement', 'retrospective_registration', 
        'Primary sponsor', 'Recruitment Status', 'Phase', 'Study type', 'Countries', 'Public title', 
        'Intervention', 'target_enrollment', 'web address', 'results yes no', 'results url link']

df_cond = df[cols].reset_index(drop=True)

#renaming columns to match old format so I don't have to change them throughout
df_cond.columns = ['TrialID', 'Source_Register', 'Date_registration', 'Date_enrollement', 
                   'retrospective_registration', 'Primary_sponsor', 'Recruitment_Status', 'Phase', 'Study_type', 
                   'Countries', 'Public_title', 'Intervention', 'target_enrollment', 'web_address', 
                   'has_results', 'results_url_link']

print(f'The ICTRP shows {len(df_cond)} trials')

# +
manual_data = parent + '/data/manual_data_for_covid_project.xlsx'

c_reg = pd.read_excel(manual_data, sheet_name = 'cross registrations')
replace_ids = c_reg.id_to_replace.tolist()

replaced = df_cond[df_cond.TrialID.isin(replace_ids)]
print(f'{len(replaced)} known cross registrations will be assessed')

df_cond_nc = df_cond[~(df_cond.TrialID.isin(replace_ids))].reset_index(drop=True)

# +
#Re-adding trials as cross-registrations

additions = pd.read_excel(manual_data, sheet_name = 'additional_trials').drop('from', 
                                                                                     axis=1).reset_index(drop=True)

print(f'An additional {len(additions)} known preferred cross registrations were added to the data')

df_cond_all = df_cond_nc.append(additions)
df_cond_all['Date_enrollement'] = df_cond_all['Date_enrollement'].apply(fix_date)

print(f'The final dataset is {len(df_cond_all)} trials')

# +
#This ensures our check for retrospective registration is accurate w/r/t cross-registrations

c_r_comp_dates = c_reg[['trial_id_keep', 'cross_reg_date']].groupby('trial_id_keep', as_index=False).min()
c_r_merged = c_r_comp_dates.merge(df_cond_nc[['TrialID', 'Date_registration', 'Date_enrollement']], 
                                 left_on='trial_id_keep', right_on='TrialID', how='left')
c_r_merged['earliest_reg'] = c_r_merged[['cross_reg_date', 'Date_registration']].min(axis=1)
pre_reg = c_r_merged[c_r_merged.TrialID.notnull() & (c_r_merged.earliest_reg <= c_r_merged.Date_enrollement)].trial_id_keep.to_list()

ret_reg = c_r_merged[c_r_merged.TrialID.notnull() & ~(c_r_merged.earliest_reg <= c_r_merged.Date_enrollement)].trial_id_keep.to_list()
ret_reg

for index, row in df_cond_all.iterrows():
    if row.TrialID in pre_reg:
        df_cond_all.at[index, 'retrospective_registration'] = True
    elif row.TrialID in ret_reg:
        df_cond_all.at[index, 'retrospective_registration'] = False

# +
#finally, add cross-registration field

df_cond_all = df_cond_all.merge(c_reg[['trial_id_keep', 'additional_ids']].drop_duplicates(), 
                              left_on='TrialID', 
                              right_on='trial_id_keep', 
                              how='left').drop('trial_id_keep', axis=1).rename(columns=
                                                                               {'additional_ids':
                                                                                'cross_registrations'}
                                                                              ).reset_index(drop=True)

df_cond_all['cross_registrations'] = df_cond_all['cross_registrations'].fillna('None')

# +
#Data cleaning various fields. 
#One important thing we have to do is make sure there are no nulls or else the data won't properly load onto the website

#semi-colons in the intervention field mess with CSV
df_cond_all['Intervention'] = df_cond_all['Intervention'].str.replace(';', '')

#Study Type
obv_replace = ['Observational [Patient Registry]', 'observational', 'Observational Study']
int_replace = ['interventional', 'Interventional clinical trial of medicinal product', 'Treatment', 
               'INTERVENTIONAL', 'Intervention', 'Interventional Study', 'PMS']
hs_replace = ['Health services reaserch', 'Health Services reaserch', 'Health Services Research']

df_cond_all['Study_type'] = (df_cond_all['Study_type'].str.replace(' study', '')
                             .replace(obv_replace, 'Observational').replace(int_replace, 'Interventional')
                             .replace('Epidemilogical research', 'Epidemiological research')
                             .replace(hs_replace, 'Health services research')
                             .replace('Others,meta-analysis etc', 'Other'))

#phase
df_cond_all['Phase'] = df_cond_all['Phase'].fillna('Not Applicable')
na = ['0', 'Retrospective study', 'Not applicable', 'New Treatment Measure Clinical Study', 'Not selected', 
      'Phase 0', 'Diagnostic New Technique Clincal Study', '0 (exploratory trials)', 'Not Specified']
p1 = ['1', 'Early Phase 1', 'I', 'Phase-1', 'Phase I']
p12 = ['1-2', '2020-02-01 00:00:00', 'Phase I/II', 'Phase 1 / Phase 2', 'Phase 1/ Phase 2',
       'Human pharmacology (Phase I): yes\nTherapeutic exploratory (Phase II): yes\nTherapeutic confirmatory - (Phase III): no\nTherapeutic use (Phase IV): no\n']
p2 = ['2', 'II', 'Phase II', 'IIb', 'Phase-2', 'Phase2',
      'Human pharmacology (Phase I): no\nTherapeutic exploratory (Phase II): yes\nTherapeutic confirmatory - (Phase III): no\nTherapeutic use (Phase IV): no\n']
p23 = ['Phase II/III', '2020-03-02 00:00:00', 'II-III', 'Phase 2 / Phase 3', 'Phase 2/ Phase 3', '2-3',
       'Human pharmacology (Phase I): no\nTherapeutic exploratory (Phase II): yes\nTherapeutic confirmatory - (Phase III): yes\nTherapeutic use (Phase IV): no\n']
p3 = ['3', 'Phase III', 'Phase-3', 'III',
      'Human pharmacology (Phase I): no\nTherapeutic exploratory (Phase II): no\nTherapeutic confirmatory - (Phase III): yes\nTherapeutic use (Phase IV): no\n']
p34 = ['Phase 3/ Phase 4', 'Phase III/IV',
       'Human pharmacology (Phase I): no\nTherapeutic exploratory (Phase II): no\nTherapeutic confirmatory - (Phase III): yes\nTherapeutic use (Phase IV): yes\n']
p4 = ['4', 'IV', 'Post Marketing Surveillance', 'Phase IV', 'PMS',
      'Human pharmacology (Phase I): no\nTherapeutic exploratory (Phase II): no\nTherapeutic confirmatory - (Phase III): no\nTherapeutic use (Phase IV): yes\n']

df_cond_all['Phase'] = (df_cond_all['Phase'].replace(na, 'Not Applicable').replace(p1, 'Phase 1')
                        .replace(p12, 'Phase 1/Phase 2').replace(p2, 'Phase 2')
                        .replace(p23, 'Phase 2/Phase 3').replace(p3, 'Phase 3').replace(p34, 'Phase 3/Phase 4')
                        .replace(p4, 'Phase 4'))

#Fixing Observational studies incorrectly given a Phase in ICTRP data
m = ((df_cond_all.Phase.str.contains('Phase')) & (df_cond_all.Study_type == 'Observational'))
df_cond_all['Phase'] = df_cond_all.Phase.where(~m, 'Not Applicable')

#Recruitment Status
df_cond_all['Recruitment_Status'] = df_cond_all['Recruitment_Status'].replace('Not recruiting', 'Not Recruiting')
df_cond_all['Recruitment_Status'] = df_cond_all['Recruitment_Status'].fillna('No Status Given')

#Get rid of messy accents
from lib.data_cleaning import norm_names
    
df_cond_all['Primary_sponsor'] = df_cond_all.Primary_sponsor.apply(norm_names)
df_cond_all['Primary_sponsor'] = df_cond_all['Primary_sponsor'].replace('NA', 'No Sponsor Name Given')
df_cond_all['Primary_sponsor'] = df_cond_all['Primary_sponsor'].replace('nan', 'No Sponsor Name Given')

# +
#Countries
df_cond_all['Countries'] = df_cond_all['Countries'].fillna('No Country Given').replace('??', 'No Country Given')

china_corr = ['Chian', 'China?', 'Chinese', 'Wuhan', 'Chinaese', 'china', 'Taiwan, Province Of China', 
              "The People's Republic of China"]

country_values = df_cond_all['Countries'].tolist()

new_list = []

for c in country_values:
    country_list = []
    if isinstance(c, float):
        country_list.append('No Sponsor Name Given')
    elif c == 'No Sponsor Name Given':
        country_list.append('No Sponsor Name Given')
    elif c in china_corr:
        country_list.append('China')
    elif c in ['Iran (Islamic Republic of)', 'Iran, Islamic Republic of']:
        country_list.append('Iran')
    elif c in ['Viet nam', 'Viet Nam']:
        country_list.append('Vietnam')
    elif c in ['Korea, Republic of', 'Korea, Republic Of', 'KOREA'] :
        country_list.append('South Korea')
    elif c in ['USA', 'United States of America', 'U.S.']:
        country_list.append('United States')
    elif c == 'Japan,Asia(except Japan),Australia,Europe':
        country_list = ['Japan', 'Australia', 'Asia', 'Europe']
    elif c == 'Japan,Asia(except Japan),North America,South America,Australia,Europe,Africa':
        country_list = ['Japan, Asia(except Japan), North America, South America, Australia, Europe, Africa']
    elif c == 'The Netherlands':
        country_list.append('Netherlands')
    elif c == 'England':
        country_list.append('United Kingdom')
    elif c == 'Japan,North America':
        country_list = ['Japan', 'North America']
    elif c == 'Czechia':
        country_list.append('Czech Republic')
    elif c == 'ASIA':
        country_list.append('Asia')
    elif c == 'EUROPE':
        country_list.append('Europe')
    elif c == 'MALAYSIA':
        country_list.append('Malaysia')
    elif c in ['Congo', 'Congo, Democratic Republic', 'Congo, The Democratic Republic of the']:
        country_list.append('Democratic Republic of Congo')
    elif c in ["C√¥te D'Ivoire", 'Cote Divoire']:
        country_list.append("Cote d'Ivoire")
    elif ';' in c:
        c_list = c.split(';')
        unique_values = list(set(c_list))
        for v in unique_values:
            if v in china_corr:
                country_list.append('China')
            elif v in ['Iran (Islamic Republic of)', 'Iran, Islamic Republic of']:
                country_list.append('Iran')
            elif v in ['Korea, Republic of', 'Korea, Republic Of', 'KOREA']:
                country_list.append('South Korea')
            elif v in ['Viet nam', 'Viet Nam']:
                country_list.append('Vietnam')
            elif v in ['USA', 'United States of America']:
                country_list.append('United States')
            elif v == 'The Netherlands':
                country_list.append('Netherlands')
            elif v == 'England':
                country_list.append('United Kingdom')
            elif v == 'Czechia':
                country_list.append('Czech Republic')
            elif v == 'ASIA':
                country_list.append('Asia')
            elif v == 'EUROPE':
                country_list.append('Europe')
            elif v == 'MALAYSIA':
                country_list.append('Malaysia')
            elif v in ['Congo', 'Congo, Democratic Republic', 'Congo, The Democratic Republic of the']:
                country_list.append('Democratic Republic of Congo')
            elif v in ["C√¥te D'Ivoire", 'Cote Divoire']:
                country_list.append("Cote d'Ivoire")
            else:
                country_list.append(v)
    else:
        country_list.append(c.strip())
    new_list.append(', '.join(country_list))

df_cond_all['Countries'] = new_list

# +
#Normalizing sponsor names
#Run this cell, updating the spon_norm csv you are loading after manual adjusting
#until you get the 'All sponsor names normalized' to print

spon_norm = pd.read_excel(manual_data, sheet_name = 'sponsor')

df_cond_norm = df_cond_all.merge(spon_norm, left_on = 'Primary_sponsor', right_on ='unique_spon_names', how='left')
df_cond_norm = df_cond_norm.drop('unique_spon_names', axis=1)

new_unique_spon_names = (df_cond_norm[df_cond_norm['normed_spon_names'].isna()][['Primary_sponsor', 'TrialID']]
                        .groupby('Primary_sponsor').count())

if len(new_unique_spon_names) > 0:
    new_unique_spon_names.to_csv('to_norm.csv')
    print('Update the normalisation schedule and rerun')
else:
    print('All sponsor names normalized')

# +
#Integrating intervention type data
#Once again, run to bring in the old int-type data, islolate the new ones, update, and rerun until
#producing the all-clear message

int_type = pd.read_excel(manual_data, sheet_name = 'intervention')
df_cond_int = df_cond_norm.merge(int_type[['trial_id', 'study_category',
                                           'intervention', 'intervention_list']], 
                                 left_on = 'TrialID', right_on = 'trial_id', how='left')

df_cond_int = df_cond_int.drop('trial_id', axis=1)

new_int_trials = df_cond_int[(df_cond_int['study_category'].isna()) | (df_cond_int['intervention'].isna())]

if len(new_int_trials) > 0:
    new_int_trials[['TrialID', 'Public_title', 'Intervention', 'study_category', 
                    'intervention', 'intervention_list']].to_csv('int_to_assess.csv')
    print('Update the intervention type assessments and rerun')
else:
    print('All intervention types matched')
    df_cond_int = df_cond_int.drop('Intervention', axis=1).reset_index(drop=True)

# +
#Final organising

col_names = []

for col in list(df_cond_int.columns):
    col_names.append(col.lower())
    
df_cond_int.columns = col_names

reorder = ['trialid', 'source_register', 'date_registration', 'date_enrollement', 'retrospective_registration', 
           'normed_spon_names', 'recruitment_status', 'phase', 'study_type', 'countries', 'public_title', 
           'study_category', 'intervention', 'intervention_list', 'target_enrollment', 'web_address', 'cross_registrations']

df_final = df_cond_int[reorder].reset_index(drop=True).drop_duplicates().reset_index()
# -

df_final.to_csv(parent + '/data/cleaned_ictrp_29June2020.csv', index=False)

# +
print(f'There are {len(df_final)} total unique registered studies on the ICTRP')

non_int = df_final[((df_final.study_type == 'Interventional') | (df_final.study_type == 'Prevention'))].reset_index(drop=True)

print(f'{len(non_int)} are Interventional or on Prevention. We exclude {len(df_final) - len(non_int)} at this setp')

in_2020 = non_int[(non_int.date_registration >= pd.Timestamp(2020,1,1))].reset_index(drop=True)

print(f'{len(in_2020)} started since 1 Jan 2020. We exclude {len(non_int) - len(in_2020)} at this step')

withdrawn = in_2020[~(in_2020.public_title.str.contains('Cancelled') | in_2020.public_title.str.contains('Retracted due to'))].reset_index(drop=True)

print(f'{len(withdrawn)} are not listed as cancelled/withdrawn. We exclude {len(in_2020) - len(withdrawn)} at this step but will exclude additional trials after scraping the registries')
# -

withdrawn.to_csv(parent + '/data/ictrp_with_exclusions_29Jul2020.csv')


