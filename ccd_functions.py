import pandas as pd
import numpy as np

import re
import math


def read_distict():
    dist = pd.read_excel('CMO_CDTractsPrecincts_May2023.xlsx')
    dist.columns = dist.columns.str.replace('\n','')\
                    .str.replace('\(.+', '_', regex=True)\
                    .str.lower().str.replace(' ', '_')\
                    .str.strip('_')
    dist = dist[['council_district2023',
                'tract_2010_id',
                'percentage_of_tract_2010_in_council_district_2023']]
    dist.columns = ['council','tract','percent']
    dist = dist.iloc[1:].reset_index(drop=True)
    dist.tract = dist.tract.astype(str)
    dist.council = np.where(dist.council.isnull(), 0, dist.council)

    return dist


def cal_counts(dist, dataall, labels, label, demon):
    demon = demon.lower()
    
    #pull out estimate and moa
    name_est = label + 'e'
    name_moa = label + 'm'

    #find the corresponding title to census label
    string = labels [labels.column_name == name_est].label.iloc[0]
    if not string.split('!!')[3:]:
        label_title = string.split('!!')[-1]
    else:
        label_title = '!!'.join(string.split('!!')[3:])

    #isolate just one indicator
    if demon == name_est:
        data = dataall[['geo_id', name_est, name_moa]].copy()
    else:
        data = dataall[['geo_id', name_est, name_moa, demon]].copy()

    #join districts and indicator together
    df = dist.merge(data, how='inner', right_on='geo_id', left_on='tract')
    df = df.replace(np.nan, 0)

    #get count percentages for each census tract per district
    df['tru_count'] = df[name_est].astype(float) * df.percent
    df['tru_error'] = df[name_moa].astype(float) * df.percent
    
    if demon == name_est:
        total_counts = df['tru_count'].astype(int).sum()
    else:
        df['tru_demon'] = df[demon].astype(float) * df.percent
        total_counts = df['tru_demon'].astype(int).sum()

    #for each council district, sum up counts, and calculate new moe
    council_counts = []

    for x in df.council.unique():
        subset = df [df.council == x]

        count = round(subset.tru_count.sum(), 2)
        count_perc = round(count / total_counts, 2)

        error = round((subset.tru_error ** 2).sum()**.5, 2)
        error_perc = round(math.sqrt(sum((subset.tru_error / 1.645)**2)) / count, 2)

        council_counts.append([x, count, count_perc, error, error_perc])

    #convert to dataframe and format
    dff = pd.DataFrame(council_counts).sort_values(0)
    dff.columns = [label_title, 'counts', 'count_perc', 'moe', 'moe_perc']
    dff = dff.set_index(label_title, drop=True)
#     print(dff)

    return dff


def cal_district_numbers(dist, dataall, labels, labels_check, demon):
    district_totals = pd.DataFrame(np.arange(11))
    totals = []

    for label in labels_check:
        dff = cal_counts(dist, dataall, labels, label, demon)
        name = dff.index.name
        dff.columns = [name + ' counts', name + ' counts percent', name + ' moe', name + ' moa percent']
        dff = dff.reset_index(drop=True)

        district_totals = pd.concat([district_totals,dff],axis=1)

    district_totals = district_totals.drop(columns=0)
    return district_totals.T