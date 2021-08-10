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

# +
import schemdraw
from schemdraw import flow

import pandas as pd
import numpy as np

from lifelines import KaplanMeierFitter
#from lifelines_fix import add_at_risk_counts
from lifelines.plotting import add_at_risk_counts
from lifelines import AalenJohansenFitter
import warnings

import matplotlib.pyplot as plt 
from matplotlib_venn import venn3, venn3_circles, venn3_unweighted
from matplotlib import pyplot as plt
# %matplotlib inline
# -

# # Setup for Survival Plots

df = pd.read_csv('https://raw.githubusercontent.com/maia-sh/direcct/master/data/reporting/kaplan-meier-time-to-pub.csv')
df.head()

# **Specific setup for Competing Risks**
#
# This prepares the dataset and does a little extra work so we can plot censors for the A-J curve.

# +
competing_risks = df[['id', 
                      'date_completion', 
                      'date_publication_any', 
                      'date_publication_article', 
                      'date_publication_preprint', 
                      'date_cutoff', 
                      'time_publication_article', 
                      'time_publication_preprint']].reset_index(drop=True)

for x in competing_risks.columns:
    if 'date' in x:
        competing_risks[x] = pd.to_datetime(competing_risks[x])

# +
cr_conds = [
    competing_risks.time_publication_preprint <= competing_risks.time_publication_article,
    (competing_risks.date_publication_article.notnull() & competing_risks.date_publication_preprint.isna())]

cr_out = [competing_risks.time_publication_preprint, competing_risks.time_publication_article]

competing_risks['time_cr'] = np.select(cr_conds, cr_out)

cr_event_conds = [
    competing_risks.date_publication_preprint.notnull(),
    competing_risks.date_publication_preprint.isna() & competing_risks.date_publication_article.notnull(),
    competing_risks.date_publication_preprint.isna() & competing_risks.date_publication_article.isna()]

cr_event_out = [1, 2, 0]

competing_risks['event_cr'] = np.select(cr_event_conds, cr_event_out)
competing_risks['time_cr'] = np.where(competing_risks['time_cr'] < 0, 0 ,competing_risks['time_cr'])
# -

d = competing_risks[['time_cr', 'event_cr']].reset_index(drop=True)
d = d.set_index('time_cr')

# +
aj = AalenJohansenFitter(seed=10)

with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    aj.fit(competing_risks.time_cr, competing_risks.event_cr, event_of_interest=1)
# -

aj_corrected = aj.cumulative_density_.reset_index()
aj_corrected = aj_corrected.set_index(aj_corrected.event_at.apply(round)).drop('event_at', axis=1)

d = aj_corrected.merge(d, how='outer', left_index=True, right_index=True)
d = d.loc[d['event_cr'] == 0].copy()

# # Individual Cumulative Incidence Curves

any_pub = df[['publication_any', 'time_publication_any']].reset_index(drop=True)
any_pub['publication_any'] = any_pub['publication_any'].astype(int)
any_pub['time_publication_any'] = np.where(any_pub['time_publication_any'] < 0, 0, any_pub['time_publication_any'])

# +
yticks = list(np.arange(0,1.05,.05))
fig = plt.figure(dpi=300)
ax = plt.subplot()

T = any_pub.time_publication_any
E = any_pub.publication_any

kmf_any = KaplanMeierFitter()
kmf_any.fit(T, E)
#ax = kmf_any.plot(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)
ax = kmf_any.plot_cumulative_density(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)

plt.title("Time To Results Dissemination From Registered Completion Date", pad=20, fontsize=20)
plt.ylabel('Proportion Reported', labelpad=10, fontsize=14)
plt.xlabel('Days to Any Result from Registered Completion', labelpad=10, fontsize=14)

from lifelines.plotting import add_at_risk_counts
add_at_risk_counts(kmf_any, rows_to_show = ['At risk'], ax=ax)
plt.tight_layout()
# -

#Use this to check when it passes 20%
kmf_any.cumulative_density_.tail(20)

article_pub = df[['publication_article', 'time_publication_article']].reset_index(drop=True)
article_pub['publication_article'] = article_pub['publication_article'].astype(int)
article_pub['time_publication_article'] = np.where(article_pub['time_publication_article'] < 0, 0, article_pub['time_publication_article'])

# +
yticks = list(np.arange(0,1.05,.05))
fig = plt.figure(dpi=300)
ax = plt.subplot()

T = article_pub.time_publication_article
E = article_pub.publication_article

kmf_article = KaplanMeierFitter()
kmf_article.fit(T, E)
#ax = kmf_any.plot(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)
ax = kmf_article.plot_cumulative_density(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)

plt.title("Time To Journal Publication From Primary Completion", pad=20, fontsize=20)
plt.ylabel('Reporting', labelpad=10, fontsize=14)
plt.xlabel('Days to Journal Publication', labelpad=10, fontsize=14)

add_at_risk_counts(kmf_article, rows_to_show = ['At risk'], ax=ax)
plt.tight_layout()

# +
yticks = list(np.arange(0,.2,.05))
fig = plt.figure(dpi=300)
ax = plt.subplot()

aj = AalenJohansenFitter(seed=10)

with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    aj.fit(competing_risks.time_cr, competing_risks.event_cr, event_of_interest=1)
aj.plot(yticks=yticks, figsize=(15,10), lw=2.5, legend=None, grid=True)
plt.plot(d.index, d['CIF_1'], '|', markersize=10, color='C0')

plt.title('Time to Preprint Publication', pad=15, fontsize=20)
plt.ylabel('Proportion Reported', labelpad=10, fontsize=15)
plt.xlabel('Days From Completion', labelpad=10, fontsize=12)


from lifelines.plotting import add_at_risk_counts
add_at_risk_counts(aj, rows_to_show = ['At risk'])
plt.tight_layout()
plt.show()
# -

# # Putting curves in a single figure

# +
figsize = (20,20)

yticks = list(np.arange(0, .75, .05))
fig = plt.figure(dpi=200)
fig.suptitle("Time to Results Across Dissemination Routes", x=.5, y=1.05, fontsize=25)

ax1 = plt.subplot(311)
kmf_any = KaplanMeierFitter().fit(any_pub.time_publication_any, any_pub.publication_any)
kmf_any.plot_cumulative_density(ci_show=True, show_censors=True, censor_styles={'ms':12, 'marker':'|'}, yticks=yticks, 
                 figsize=figsize, grid=True, legend=False, ax=ax1, lw=2.5, color = '#2D8E87')

plt.ylabel('Proportion Reported', labelpad=10, fontsize=14)
plt.xlabel('Days From Completion', labelpad=10, fontsize=14)
plt.title('Time to Any Results Dissemination', pad=15, fontsize=18)
plt.yticks(yticks)

ax1.tick_params(labelsize=14)
add_at_risk_counts(kmf_any, labels=[''], rows_to_show = ['At risk'], ax=ax1, fontsize=14)

#Plot 2
ax2 = plt.subplot(312)
kmf_article = KaplanMeierFitter().fit(article_pub.time_publication_article, article_pub.publication_article)
kmf_article.plot_cumulative_density(ci_show=True, show_censors=True, censor_styles={'ms':12, 'marker':'|'}, yticks=yticks, 
                 figsize=figsize, grid=True, legend=False, ax=ax2, lw=2.5, color = '#2D8E87')

plt.ylabel('Proportion Reported', labelpad=10, fontsize=14)
plt.xlabel('Days From Completion', labelpad=10, fontsize=14)
plt.title('Time to Journal Publication', pad=15, fontsize=18)
plt.yticks(yticks)

ax2.tick_params(labelsize=14)
add_at_risk_counts(kmf_article, labels=[''], rows_to_show = ['At risk'], ax=ax2, fontsize=14)

#plot3
ax3 = plt.subplot(313)
aj = AalenJohansenFitter(seed=10)
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    aj.fit(competing_risks.time_cr, competing_risks.event_cr, event_of_interest=1)
aj.plot(yticks=yticks, figsize=figsize, lw=2.5, legend=None, grid=True, ax=ax3, color = '#2D8E87')
plt.plot(d.index, d['CIF_1'], '|', markersize=12, color='C0', markeredgecolor='#2D8E87')

plt.ylabel('Proportion Reported', labelpad=10, fontsize=14)
plt.xlabel('Days From Completion', labelpad=10, fontsize=14)
plt.title('Time to Preprint Publication', pad=15, fontsize=18)
plt.yticks(yticks)

ax3.tick_params(labelsize=14)
add_at_risk_counts(aj, labels=[''], rows_to_show = ['At risk'], ax=ax3, fontsize=14)

plt.subplots_adjust(hspace=.2)
plt.tight_layout()
plt.show()
#fig.savefig('Figures/km_curves.jpeg')
# -

# # 3 month follow-up data

df_3mon = pd.read_csv('https://raw.githubusercontent.com/maia-sh/direcct/master/data/reporting/kaplan-meier-time-to-pub_3-mo.csv')

any_pub_3 = df_3mon[['publication_any', 'time_publication_any']].reset_index(drop=True)
any_pub_3['publication_any'] = any_pub_3['publication_any'].astype(int)
any_pub_3[any_pub_3 < 0] = 0

# +
yticks = list(np.arange(0,.75,.1))
fig = plt.figure(dpi=300)
ax = plt.subplot()

kmf_3mo = KaplanMeierFitter()
kmf_3mo.fit(any_pub_3.time_publication_any, any_pub_3.publication_any)
#ax = kmf_any.plot(ci_show=False, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)
ax = kmf_3mo.plot_cumulative_density(ci_show=True, show_censors=True, censor_styles={'ms':10, 'marker':'|'}, 
                                     yticks=yticks, figsize=(15, 10), grid=True, legend=False, ax=ax, lw=2.5)

plt.title("Time To Results Dissemination From Registered Completion Date - Extended Follow-up", pad=20, fontsize=20)
plt.ylabel('Proportion Reported', labelpad=10, fontsize=14)
plt.xlabel('Days to Any Result from Registered Completion', labelpad=10, fontsize=14)
plt.yticks(yticks)
ax.tick_params(labelsize=12)

from lifelines.plotting import add_at_risk_counts
add_at_risk_counts(kmf_3mo, rows_to_show = ['At risk'], ax=ax, fontsize=12)
plt.tight_layout()
#plt.savefig('Figures/extended_km.jpeg')
# -

# # Flowchart - Inclusion/Exclusion

# +
d = schemdraw.Drawing()
bw = 7
bh =2

total = d.add(flow.Box(w=10, h=2, label= 'Registered COVID-19 Studies on ICTRP\n(N=3,844)'))
d.add(flow.Arrow('down', l=11))
d.add(flow.Arrow('right', at=(0, -3.5)))
cross_reg = d.add(flow.Box(w=bw, h=bh, label=f'Known Cross-Registrations\n(n={3844-3749})', anchor='W'))
d.add(flow.Arrow('right', at=(0, -6)))
pre2020 = d.add(flow.Box(w=bw, h=bh, label='Registered Prior to 2020\n(n=18)', anchor='W'))
d.add(flow.Arrow('right', at=(0,-8.5)))
non_int = d.add(flow.Box(w=bw, h=bh, label='Not Interventional\n(n=1,565)', anchor='W'))
d.add(flow.Arrow('right', at=(0,-11)))
withdrawn = d.add(flow.Box(w=bw, h=bh, label='Withdrawn on ICTRP\n(n=45)', anchor='W'))

auto_total = d.add(flow.Box(w=10, h=2, at=(0,-13), label='Passed Automated Inclusion\n(n=2121)'))
d.add(flow.Arrow('down', l=13))
d.add(flow.Arrow('right', at=(0, -16.5)))
completed = d.add(flow.Box(w=bw, h=bh, label='Completion > 30 June 2020\n(n=1,724)', anchor='W'))
d.add(flow.Arrow('right', at=(0, -19)))
not_trial = d.add(flow.Box(w=bw, h=bh, label='Not a Clincial Trial\n(n=22)', anchor='W'))
d.add(flow.Arrow('right', at=(0, -21.5)))
not_covid = d.add(flow.Box(w=bw, h=bh, label='Not on Treatment/Prevention\n(n=83)', anchor='W'))
d.add(flow.Arrow('right', at=(0, -24)))
withdrawn_2 = d.add(flow.Box(w=bw, h=bh, label='Withdrawn on Manual Review\n(n=5)', anchor='W'))
d.add(flow.Arrow('right', at=(0, -26.5)))
man_dupes = d.add(flow.Box(w=bw, h=bh, label='Manual De-duplication\n(n=2)', anchor='W'))

final_total = d.add(flow.Box(w=10, h=2, at=(0,-28), label='Final Dataset\n(n=285)'))

#d.save('Figures/flowchart_covid_2021.jpeg', dpi=300)
d.draw()
# -

# # Flow Chart - Results

# +
d = schemdraw.Drawing()
total = d.add(flow.Box(w=8, h=2, label= '124 Results Located'))
d.add(flow.Arrow('down', l=16))
d.add(flow.Arrow('right', at=(0, -3.5)))
no_trial_id = d.add(flow.Box(w=6.5, h=2, label=f'Could not link to trial ID\n(n=5)', anchor='W'))
d.add(flow.Arrow('right', at=(0, -6)))
no_comp = d.add(flow.Box(w=6.5, h=2, label='No known completion date\n(n=8)', anchor='W'))
d.add(flow.Arrow('right', at=(0,-8.5)))
post_cutoff = d.add(flow.Box(w=6.5, h=2, label='Registered Completion\nafter 30 June 2020\n(n=23)', anchor='W'))
d.add(flow.Arrow('right', at=(0,-11)))
pub_missing = d.add(flow.Box(w=6.5, h=2, label='No publication date\n(n=1)', anchor='W'))
d.add(flow.Arrow('right', at=(0, -13.5)))
post_follow_up = d.add(flow.Box(w=6.5, h=2, label='Published after\n15 August 2020\n(n=39)', anchor='W'))
d.add(flow.Arrow('right', at=(0,-16)))
excluded = d.add(flow.Box(w=6.5, h=2, label='Publication identified\nas retrosepctive\n(n=1)', anchor='W'))
final_total = d.add(flow.Box(w=10, h=2, at=(0,-18), label='Results Included\n(n=47)'))

#d.save('Figures/results_flowchart_covid_2021.jpeg', dpi=300)
d.draw()
# -
# # Venn Diagram

# +
colors = ['#377eb8', '#ff7f00', '#4daf4a','#f781bf', '#a65628', '#984ea3', '#999999', '#e41a1c', '#dede00']
labels = ['Journal Articles', 'Registry Results', 'Preprints']
values = (14, 2, 0, 21, 4, 0, 0)


# +
plt.figure(figsize=(8,8), dpi=300)
v1 = venn3(
    subsets = values, 
    set_labels = labels,
    set_colors = colors, 
    subset_label_formatter = lambda x: str(x) + "\n(" + f"{(x/sum(values)):1.2%}" + ")", 
    alpha = .6)

for text in v1.set_labels:
    text.set_fontsize(9)

venn3_circles((14, 2, 0, 21, 4, 0, 0))
plt.title('COVID-19 Clinical Trial Results by Dissemination Route', fontweight='bold')
#plt.savefig('Figures/venn_diagram.jpeg')
# -


