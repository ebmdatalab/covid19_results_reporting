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

import sys
from pathlib import Path
import os
cwd = os.getcwd()
parent = str(Path(cwd).parents[0])
sys.path.append(parent)

import pandas as pd
import numpy as np

df = pd.read_csv(parent + '/data/cleaned_ictrp_29June2020.csv').drop('index', axis=1)

df['date_registration'] = pd.to_datetime(df['date_registration'])

df.head()


# +
def dedupe_check(df, fields):
    check = df[fields].groupby(fields[0], as_index=False).count().sort_values(by='source_register', ascending=False)
    return check[check.source_register > 1]

dedupe_check(df, ['trialid', 'source_register'])

# +
#exclusion logic

int_prev = ((df.study_type == 'Interventional') | (df.study_type == 'Prevention'))

in_2020 = (df.date_registration >= pd.Timestamp(2020,1,1))

#At the moment, this deals with withdrawn trials from the ChiCTR. Data from other registries doesn't
#Reliable make it to the ICTRP. We will exclude withdrawn trials from ClinicalTrials.gov
#When we join that in below.
withdrawn = ~((df.public_title.str.contains('Cancelled')) | df.public_title.str.contains('Retracted due to'))
# -

df['included'] = np.where(int_prev & in_2020 & withdrawn, 1, 0)

registry_data = pd.read_csv(parent + '/data/registry_data/registry_data_clean.csv')

registry_data.head()

# +
#Taking only what we need to join
reg_cols = ['trial_id', 'trial_status', 'pcd', 'scd', 'relevant_comp_date', 'tabular_results', 
            'potential_other_results']


df_reg_merge = df.merge(registry_data[reg_cols], how='left', left_on='trialid', 
                        right_on='trial_id').drop('trial_id', axis=1)

df_reg_merge['tabular_results'] = df_reg_merge['tabular_results'].fillna(0).astype(int)
df_reg_merge['potential_other_results'] = df_reg_merge['potential_other_results'].fillna(0).astype(int)

# +
#excluding more withdrawn trials

df_reg_merge['included'] = np.where((df_reg_merge.trial_status == 'Withdrawn'), 0, df_reg_merge['included'])
df_reg_merge = df_reg_merge.drop('trial_status', axis=1)
# -

dedupe_check(df_reg_merge, ['trialid', 'source_register'])

auto_hits = pd.read_csv(parent + '/data/screening_hit_results.csv')

# Note:
#
# We have to change EUCTR2020-000890-25 to "EUCTR2020-000890-25-FR" and "EUCTR2020-001934-37" to "EUCTR2020-001934-37-ES" to match how they appear in the ICTRP for merging

auto_hits['trn_1'] = auto_hits['trn_1'].str.replace('EUCTR2020-000890-25', 'EUCTR2020-000890-25-FR').str.replace('EUCTR2020-001934-37', 'EUCTR2020-001934-37-ES')

# +
#Here we remove the record PMID32339248 as this was a duplicate PubMed entry to 32330277. 
#We contacted PubMed and this has now been deleted from PubMed entirely.

auto_hits = auto_hits[auto_hits.id != '32339248'].reset_index(drop=True)


# +
def group_rules(grp):
    l = []
    for x in grp:
        if x in l:
            pass
        else:
            l.append(x)
    if len(l) == 0:
        return np.nan
    else:
        return l

def max_list_size(column):
    max_size = 0
    for x in column:
        if len(x) > max_size:
            max_size = len(x)
    return max_size


# +
group_auto = auto_hits.groupby('trn_1', as_index=False).agg(group_rules)

filtered = group_auto[['trn_1', 'trn_2', 'id', 'doi', 'results_pub_type',  
                       'completion_date', 'publication_date']].reset_index(drop=True)

rename = ['hit_tid', 'hit_tid2', 'auto_id', 'doi', 'results_pub_type', 'pub_completion_date', 'publication_date']

filtered.columns = rename

# +
for name in rename[2:]:
    col_list = filtered[name].tolist()
    max_size = max_list_size(col_list)
    cols = [(name + '_{}').format(x) for x in range(1, max_size+1)]
    filtered[cols] = pd.DataFrame(col_list, index=filtered.index)
    filtered = filtered.drop(name, axis=1)

#Fixing this
filtered['hit_tid2'] = filtered['hit_tid2'].str[0]
# -

df_final = df_reg_merge.merge(filtered, how='left', left_on='trialid', right_on='hit_tid').drop('hit_tid', axis=1)

dedupe_check(df_final, ['trialid', 'source_register'])

# +
#Check for trials that are in our results but not in the ICTRP dataset

a = df_reg_merge.trialid.tolist()
b = filtered.hit_tid.tolist()

set(b) - set(a)

# +
df_final['relevant_comp_date'] = pd.to_datetime(df_final['relevant_comp_date'])

df_final.columns

# +
#Conditions for round inclusion:

overall_inclusion = (df_final.included == 1)
date_inclusion = (df_final.relevant_comp_date < pd.Timestamp(2020,7,1))
reg_or_pub = ((df_final.results_pub_type_1.notnull()) | (df_final.tabular_results == 1) | (df_final.potential_other_results == 1))


df_final["round_inclusion"] = np.where((overall_inclusion & (date_inclusion | reg_or_pub)),1,0)
# -

df_final.head()

df_final.round_inclusion.sum()

df_final.to_csv(parent + '/data/final_dataset.csv')




