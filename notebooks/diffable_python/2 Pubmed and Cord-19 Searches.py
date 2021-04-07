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

# This notebook performs the searches of PubMed and the CORD-19 Database for text representing trial registrations.

# # PubMed Search

# +
import sys
from pathlib import Path
import os
cwd = os.getcwd()
parent = str(Path(cwd).parents[0])
sys.path.append(parent)

# %load_ext autoreload
# %autoreload 2

# +
import os
from tqdm.auto import tqdm
import re
import json
import pandas as pd
import numpy as np
import xmltodict

from bs4 import BeautifulSoup
from xml.etree.ElementTree import tostring

# +
#If the archive exists, load it in.
try:
    from lib.id_searches import zip_load
    archive_df = zip_load(parent + '/data/pubmed/pubmed_archive_1July_2020.csv.zip', 
                  'pubmed_archive_1July_2020.csv', index_col = 0)

#If it doesn't exist, you can do a new PubMed search
except FileNotFoundError:
    from pymed import PubMed
    from lib.credentials import email
    from lib.id_searches import query, create_pubmed_archive
    print('Archive file not found, conduting new PubMed search.')
    pubmed = PubMed(tool="Pymed", email=email)
    results = pubmed.query(query, max_results=100000)
    
    print('Transforming results. This may take a few minutes')
    results_list = list(results) #This can take a while
    
    archive_df = create_pubmed_archive(results_list)
    archive_df.to_csv(parent + '/data/pubmed/pubmed_archive_1July_2020.csv')
    
# -

pubmed_data = archive_df.xml_json.tolist()

# +
pubmed_dicts = []
for rec in tqdm(pubmed_data):
    pm_dict = json.loads(rec)['PubmedArticle']
    entry_dict = {}
    art_ids = pm_dict['PubmedData']['ArticleIdList']['ArticleId']
    entry_dict['source'] = 'PubMed'
    entry_dict['pmid'] = pm_dict['MedlineCitation']['PMID']['#text']
    entry_dict['doi'] = None
    if isinstance(art_ids, list):
        for x in art_ids:
            if x['@IdType'] == 'doi':
                entry_dict['doi'] = x['#text']
    elif isinstance(art_ids, dict):
        if art_ids['@IdType'] == 'doi':
            entry_dict['doi'] = art_ids['#text']
    try:
        dbs =  pm_dict['MedlineCitation']['Article']['DataBankList']['DataBank']
        accession_nums = []
        if isinstance(dbs, list):
            for x in dbs:
                ans = x['AccessionNumberList']['AccessionNumber']
                if isinstance(ans, list):
                    accession_nums += ans
                else:
                    accession_nums.append(x)
        elif isinstance(dbs, dict):
            x = dbs['AccessionNumberList']['AccessionNumber']
            if isinstance(x, list):
                accession_nums += x
            else:
                accession_nums.append(x)
                
        if accession_nums:
            entry_dict['accession'] = accession_nums
        else:
            entry_dict['accession'] = None
    except KeyError:
        entry_dict['accession'] = None
    
    try:
        entry_dict['abstract'] = str(pm_dict['MedlineCitation']['Article']['Abstract']['AbstractText'])
    except KeyError:
        entry_dict['abstract'] = None
    
    try:
        entry_dict['pub_types'] = pm_dict['MedlineCitation']['Article']['PublicationTypeList']
    except KeyError:
        entry_dict['pub_types'] = None
    pubmed_dicts.append(entry_dict)


# +
#Our searching function and lists of our regular expressions
from lib.id_searches import search_text, ids_exact, prefixes, registry_names

for d in tqdm(pubmed_dicts):
    d['abst_id_hits'] = search_text(ids_exact, d['abstract'])
    d['reg_prefix_hits'] = search_text(prefixes, d['abstract'])
    d['reg_name_hits'] = search_text(registry_names, d['abstract'])


# -

pubmed_search_results = pd.DataFrame(pubmed_dicts)

# +
col_order = ['pmid', 'source', 'abst_id_hits', 'reg_prefix_hits', 'reg_name_hits', 'accession', 'pub_types', 'doi']
col_rename = ['id', 'source', 'id_hits', 'prefix_hits', 'reg_name_hits', 'accession', 'pub_types', 'doi']

final_pubmed = pubmed_search_results[col_order].reset_index(drop=True)
final_pubmed.columns = col_rename
final_pubmed['pm_id'] = final_pubmed['id']
final_pubmed['cord_id'] = None
# -

final_pubmed.to_csv(parent + '/data/pubmed/pubmed_search_results.csv')

# # Searching CORD-10 data

metadata = zip_load(parent + '/data/cord_19/metadata.csv.zip', 'metadata.csv', low_memory = False)
metadata['publish_time'] = pd.to_datetime(metadata['publish_time'])

# +
#Getting a list of all the filenames for the papers that were published in 2020
covid_19_arts = metadata[metadata.publish_time >= pd.Timestamp(2020,1,1)].sha.to_list()
covid_19_pmc = metadata[metadata.publish_time >= pd.Timestamp(2020,1,1)].pmcid.to_list()
recent_articles = []
for c in covid_19_arts:
    recent_articles.append(str(c) + '.json')

recent_pmcs = []
for p in covid_19_pmc:
    recent_pmcs.append(str(p) + '.xml.json')

# +
#The CORD-19 document parses are too big to fit in the GitHub repo so you need to download and add locally
#All versions of the CORD-19 database can be accessed here: 
#https://ai2-semanticscholar-cord-19.s3-us-west-2.amazonaws.com/historical_releases.html
path_pre = parent + '/data/cord_19/document_parses/'

pdfs = os.listdir(path_pre + 'pdf_json')
pmc = os.listdir(path_pre + 'pmc_json')

# +
#Now we can only pull out the recent articles from the pdfs
overlap_pdf = list(set(recent_articles).intersection(set(pdfs)))

overlap_pmc = list(set(recent_pmcs).intersection(set(pmc)))

# +
#These are searches in the CORD-19 database and take roughly an hour to run both.
from lib.id_searches import search_text, ids_exact, prefixes, registry_names

cord_pdf_list = []

for o in tqdm(overlap_pdf):
    with open(path_pre + 'pdf_json' + '/' + o, 'r') as x:
        doc_dict = {}
        c_text = x.read()
        a = json.loads(c_text)
        doc_dict['file_name'] = a['paper_id']
        doc_dict['source'] = 'cord_pdf'
        doc_dict['id_hits'] = search_text(ids_exact, c_text)
        doc_dict['reg_prefix_hits'] = search_text(prefixes, c_text)
        doc_dict['reg_name_hits'] = search_text(registry_names, c_text)
    cord_pdf_list.append(doc_dict)

# +
cord_pmc_list = []

for o in tqdm(overlap_pmc):
    with open(path_pre + 'pmc_json' + '/' + o, 'r') as x:
        doc_dict = {}
        c_text = x.read()
        a = json.loads(c_text)
        doc_dict['file_name'] = a['paper_id']
        doc_dict['source'] = 'cord_pmc'
        doc_dict['id_hits'] = search_text(ids_exact, c_text)
        doc_dict['reg_prefix_hits'] = search_text(prefixes, c_text)
        doc_dict['reg_name_hits'] = search_text(registry_names, c_text)
    cord_pmc_list.append(doc_dict)

# +
cord_pmc_df = pd.DataFrame(cord_pmc_list)

final_pmc = cord_pmc_df.merge(metadata, left_on='file_name', right_on='pmcid', how='left')

# +
cord_pdf_df = pd.DataFrame(cord_pdf_list)

final_pdf = cord_pdf_df.merge(metadata, left_on='file_name', right_on='sha', how='left')

# +
col_order = ['id', 'source', 'id_hits', 'reg_prefix_hits', 'reg_name_hits', 'accession', 'pub_types', 'doi', 
             'pubmed_id', 'cord_uid']
col_names = ['id', 'source', 'id_hits', 'prefix_hits', 'reg_name_hits', 'accession', 'pub_types', 'doi', 'pm_id', 'cord_id']

interim_cord = final_pmc.append(final_pdf, ignore_index=True).reset_index(drop=True)

interim_cord['id'] = np.where(interim_cord.pubmed_id.isna(), interim_cord.cord_uid, interim_cord.pubmed_id)
interim_cord['accession'] = None
interim_cord['pub_types'] = None

final_cord = interim_cord[col_order].reset_index(drop=True)
final_cord.columns = col_names
# -

final_cord.to_csv(parent + '/data/cord_19/cord_19_search_results.csv')

# # Final Data Management

combined_dataset = final_cord.append(final_pubmed, ignore_index=True)
combined_dataset.head()

# +
#need to turn the pub_types column into strings:
from lib.id_searches import stringify

combined_dataset['pub_types'] = combined_dataset.pub_types.apply(stringify)

# +
filter_1 = combined_dataset.id_hits.notnull()

filter_2 = combined_dataset.prefix_hits.notnull()

filter_3 = combined_dataset.reg_name_hits.notnull()

filter_4 = combined_dataset.accession.notnull() & (combined_dataset.accession != '[]')

filter_5 = combined_dataset.pub_types.str.contains(re.compile('(?i)Trial'))
# -

filtered = combined_dataset[filter_1 | filter_2 | filter_3 | filter_4 | filter_5].sort_values('id').reset_index(drop=True).fillna(np.nan)

# +
from lib.id_searches import add_lists, make_doi_url, trial_pub_type

combined = filtered[['id', 'id_hits', 'prefix_hits', 'reg_name_hits', 'accession']].groupby('id').agg(add_lists).merge(
    filtered[['id', 'pub_types']][filtered.pub_types.notnull()], how='left', left_on='id', right_on='id').merge(
    filtered[['id', 'doi', 'pm_id']].drop_duplicates(), how='left', left_on='id', right_on='id').merge(
    filtered[['id','cord_id']][filtered.cord_id.notnull()].drop_duplicates(), how='left', left_on='id', right_on='id')

combined['doi'] = combined.doi.apply(make_doi_url)
combined['pub_types'] = combined.pub_types.apply(trial_pub_type)
# -

final = combined.merge(metadata[['cord_uid', 'url', 'title']], how='left', left_on='cord_id', right_on='cord_uid').drop('cord_uid', axis=1)

#Do a final dedupe
final_deduped = final.drop_duplicates('id').reset_index(drop=True)

final_deduped.to_csv(parent + '/data/final_auto_15Sept2020.csv')
