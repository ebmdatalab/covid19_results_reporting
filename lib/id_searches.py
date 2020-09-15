from zipfile import ZipFile
from pandas import read_csv, DataFrame
import numpy as np
from tqdm.auto import tqdm
from pymed import PubMed
import xmltodict
import re


ids_exact = ['(?i)NCT\s*\W*0\d{7}', '20\d{2}\W*0\d{5}\W*\d{2}', '(?i)PACTR\s*\W*20\d{13}', '(?i)ACTRN\s*\W*126\d{11}', 
            '(?i)ANZCTR\s*\W*126\d{11}', '(?i)NTR\s*\W*\d{4}', '(?i)KCT\s*\W*00\d{5}', '(?i)DRKS\s*\W*000\d{5}', 
            '(?i)ISRCTN\s*\W*\d{8}', '(?i)ChiCTR\s*\W*20000\d{5}', '(?i)IRCT\s*\W*20\d{10,11}N\d{1,3}', 
            '(?i)CTRI\s?\W*\/\s*\W*202\d{1}\s?\W*\/\s*\W*\d{2,3}\s*\W*\/\s*\W*0\d{5}', '(?i)Japic\s*CTI\s*\W*\d{6}', 
            '(?i)jrct\W*\w{1}\W*\d{9}', '(?i)UMIN\s*\W*\d{9}', '(?i)JMA\W*IIA00\d{3}', '(?i)RBR\s*\W*\d\w{5}', 
            '(?i)RPCEC\s*\W*0{5}\d{3}', '(?i)LBCTR\s*\W*\d{10}', '(?i)SLCTR\s*\W*\d{4}\s*\W*\d{3}', 
            '(?i)TCTR\s*\W*202\d{8}', '{?i}PER\s*\W*\d{3}\s*\W*\d{2}']


#There are currently no relevant Peruvian trial registered for COVID-19 via the ICTRP dataset and
#including it here leads to lots of false positives, so for the moment I am removing.
#For future, regex is r'(?i)\bPER\d*\b'
prefixes = [r'(?i)\bNCT', r'(?i)\bEudraCT', r'(?i)\bEUCTR', r'(?i)\bPACTR', r'(?i)\bACTRN', r'(?i)\bANZCTR', 
            r'(?i)\bNTR\d*\b', r'(?i)\bKCT', r'(?i)\bDRKS', r'(?i)\bISRCTN', r'(?i)\bChiCTR', r'(?i)\bIRCT', 
            r'(?i)\bCTRI', r'(?i)\bJapic\s*CTI', r'(?i)\bjRCT', r'(?i)\bUMIN', r'(?i)\bRBR', r'(?i)\bRPCEC', 
            r'(?i)\bLBCTR', r'(?i)\bSLCTR', r'(?i)\bTCTR']

registry_names = ['(?i)clinicaltrials.gov', '(?i)European Union Clinical Trials Register', 
                  '(?i)Pan African Clinical Trial Registry', 'Australian New Zealand Clinical Trials Registry',
                  '(?i)Netherlands Trial Register', '(?i)Clinical Research Information Service', 
                  '(?i)German Clinical Trials Register', '(?i)Chinese Clinical Trial Registry', 
                  '(?i)Iranian Registry of Clinical Trials', '(?i)Clinical Trials Registry-India', 
                  '(?i)JAPIC Clinical Trial Information', '(?i)Japan Registry of Clinical Trial', 
                  '(?i)UMIN Clinical Trials Registry', '(?i)Brazilian Clinical Trial Registry', 
                  '(?i)Cuban Public Registry of Clinical Trials', '(?i)Lebanese Clinical Trials Registry', 
                  '(?i)Sri Lanka Clinical Trials Registry', '(?i)Thai Clinical Trials Registry',
                  '(?i)Peruvian Clinical Trial Registry']

#From https://osf.io/xczyn/
query = 'coronavirus*[ti] OR corona virus*[ti] OR covid*[ti] OR sars[ti] OR severe acute respiratory syndrome[ti] OR ncov*[ti] OR "severe acute respiratory syndrome coronavirus 2" [Supplementary Concept] OR "COVID-19" [Supplementary Concept] OR (wuhan[tiab] AND (coronavirus[tiab]OR coronavirus[tiab]OR pneumonia virus[tiab])) OR COVID19[tiab] OR COVID-19[tiab] OR coronavirus-2019[tiab] OR corona-virus-2019[tiab] OR SARS-CoV-2[tiab] OR SARSCoV-2[tiab] OR SARSCoV2[tiab] OR SARS2[tiab] OR SARS-2[tiab] OR "severe acute respiratory syndrome 2"[tiab] OR 2019-nCoV[tiab] OR ((novel coronavirus[tiab]OR novel corona virus[tiab])AND 2019[tiab])NOT (animals[mesh] NOT humans[mesh])AND ("2019/12/01"[EDAT] : "3000/12/31"[EDAT])'

def zip_load(path, file, index_col=None, low_memory=True):
      zip_file = ZipFile(path)
      return read_csv(zip_file.open(file), index_col=index_col, low_memory=low_memory)


def create_pubmed_archive(results_list):
      archive = []
      for r in tqdm(results_list):
            pm_dict = r.toDict()
            try:
                  xml = pm_dict['xml']
            except KeyError:
                  continue
            pm_dict['xml_json'] = json.dumps(xmltodict.parse(tostring(xml), dict_constructor=dict))
            archive.append(pm_dict)
      return DataFrame(archive)

def search_text(regex_list, to_search):
      hits = []
      for reg in regex_list:
            check = re.compile(reg)
            if to_search:
                  result = re.findall(check, to_search)
                  hits = hits + result
      if hits:
            return hits
      else:
            return None

def add_lists(grp):
    master_list = []
    for x in grp:
        if isinstance(x, list):
            master_list += x
    if master_list:
        return list(set(master_list))
    else:
        return np.nan

def make_doi_url(x):
    if isinstance(x,str):
        return 'http://doi.org/' + x
    else:
        return x

def trial_pub_type(x):
    if not isinstance(x, float) and (('Trial' in x) or ('trial' in x)):
        return 'Has Trial Pub Type'
    else:
        return np.nan

def stringify(x):
      if not isinstance(x,float):
            return str(x)
      else:
            return x
