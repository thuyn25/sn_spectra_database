'''
author:        thuyn25 <thuyn27@lsu.edu>
date:          2026-03-24 15:00:31

This script is used for pre-processing raw spectra and create SNlist.txt
'''
import glob 
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from astropy.time import Time
from auxiliary import clean_name


# from auxiliary import load_lines
# from specload import read_spec
# from remove_tellurics import remove_tellurics, degrade_telluric

#---------------------------------- MAKE SNlist.txt ---------------------------------
osc_path = '../data/raw/osc_metadata.csv'
tns_path = '../data/raw/tns_metadata.csv'
wiserep_path = '../data/raw/wiserep_metadata.csv'
liu17_path = '../data/raw/SLSNIc-LiuModjazBianco17-infolist.txt'
dtype=[('name','<U16'),('redshift',np.float64),('E(B-V)',np.float64),('temperature',np.float64),('note','<U15'), ('max_MJD','<U10'),('max_date','<U10'),('startpos','<U3'),('obs_band','<U3'),('note1','<U15')]

osc = pd.read_csv(osc_path)
tns = pd.read_csv(tns_path)
wis = pd.read_csv(wiserep_path)
print('original', len(wis))
#------------------------------------------------------------------------


#------------------------------------------------------------------------
# Contain max_date of some events
liu17_data = np.genfromtxt(liu17_path, dtype=dtype, skip_header=1)
liu17_data['max_MJD'] = np.array([s.split('(')[0] for s in liu17_data['max_MJD']])
liu17_df = pd.DataFrame(liu17_data)
names = []
max_dates = []
for name, t in zip(liu17_df['name'], liu17_df['max_MJD']):
    new_name = clean_name(name)
    names.append(new_name)

    date = Time(t, format='mjd', scale='utc')
    date = (date.to_value('iso'))
    parts = date.split(' ')
    max_dates.append(parts[0])
liu17_df['sn_name'] = names
liu17_df['max_brightness_date'] = max_dates
# print(liu17_df.columns)
#------------------------------------------------------------------------


#------------------------------------------------------------------------
# Contain no max_date nor discovery_date
wis['IAU name'] = wis['IAU name'].fillna('')
wis['Internal name/s'] = wis['Internal name/s'].fillna('')
def get_primary_name(row):
    name = row['IAU name'].strip()
    if name and name.lower() != 'nan':
        return name
    
    internal = row['Internal name/s'].strip()
    if internal and internal.lower() != 'nan':
        # Split by comma or slash and take the first piece
        name = internal.replace('/', ',').split(',')[0].strip()
        return name
    name = f"iPTF16eh"
    return name
wis['sn_name'] = wis.apply(get_primary_name, axis=1)
wis['sn_name'] = wis['sn_name'].apply(clean_name)
#------------------------------------------------------------------------


#------------------------------------------------------------------------
# Contain only discovery_date
names = []
disdates = []
new_name = ''
for name, utdate in zip(tns['Name'], tns['Discovery Date (UT)']):
    new_name = clean_name(name)
    names.append(new_name)

    date = utdate.split(' ')[0]
    disdates.append(date)
tns['sn_name'] = names
tns['discovery_date'] = disdates
#------------------------------------------------------------------------


#------------------------------------------------------------------------
# Contain both max_date (some) + discovery_date
names = []
new_name = ''
for name in osc['sn_name']:
    new_name = clean_name(name)
    names.append(new_name)
osc['sn_name'] = names
#------------------------------------------------------------------------
# Check total numbers of unique events with spectra
osc_spec_dir = '../data/raw/osc_raw_data_20260325'
wis_spec_dir = '../data/raw/wiserep_rename_data_20260325_130547'
osc_infiles = glob.glob(osc_spec_dir+"/*.dat")
wis_infiles = glob.glob(wis_spec_dir+"/*")
osc_sne = []
wis_sne = []

for f in osc_infiles:
    fname = os.path.basename(f)
    sn_name = fname.split('_')[0]
    osc_sne.append(sn_name)
    
for f in wis_infiles:
    fname = os.path.basename(f)
    sn_name = fname.split('_')[0]
    wis_sne.append(sn_name)

unique_osc_folder = set(osc_sne)
unique_wis_folder = set(wis_sne)
wis_metadata_names = set(wis['sn_name'].unique())
osc_metadata_names = set(osc['sn_name'].unique())

print(f"--- WISeREP Statistics ---")
print(f"Total files in folder: {len(wis_infiles)}")
print(f"Unique SN names extracted from folder: {len(unique_wis_folder)}")
print(f"Unique SN names in metadata: {len(wis_metadata_names)}")

# Check for mismatches
mismatched = unique_wis_folder - wis_metadata_names
if mismatched:
    print(f"WARNING: {len(mismatched)} names in folder are NOT in metadata: {list(mismatched)[:5]}...")

print(f"\n--- OSC Statistics ---")
print(f"Total files in folder: {len(osc_infiles)}")
print(f"Unique SN names in folder: {len(unique_osc_folder)}")
print(f"Unique SN names in metadata: {len(osc_metadata_names)}\n")
#------------------------------------------------------------------------


#------------------------------------------------------------------------
# all_sne = sorted(list(set(wis['sn_name'].tolist() + osc['sn_name'].tolist())))
unique_wis = wis_metadata_names
unique_osc = osc_metadata_names

duplicate_names = unique_wis.intersection(unique_osc)
print(f"Number of SNe found in both WISeREP and OSC: {len(duplicate_names)}")
print("Duplicate names list:", sorted(list(duplicate_names)))
all_sne = unique_osc.union(unique_wis)
print(f"Total unique SLSNe: {len(all_sne)}")

sn_list_data = []

for name in all_sne:
    row_wis = wis[wis['sn_name'] == name]
    row_osc = osc[osc['sn_name'] == name]
    # print(row_wis, row_osc)
    # break

    if not row_wis.empty:
        sn_type = row_wis.iloc[0]['Obj. Type']
        z = row_wis.iloc[0]['Redshift']
    elif not row_osc.empty:
        sn_type = row_osc.iloc[0]['sn_type']
        z = row_osc.iloc[0]['redshift']
    else:
        print(f'{name} does not have info saved...Debug')
        continue

    max_date = 'unknown'
    discovery_date = 'unknown'
    
    if name in liu17_df['sn_name'].values:
        max_date = liu17_df.loc[liu17_df['sn_name'] == name, 'max_brightness_date'].values[0]
        if name in tns['sn_name'].values:
            discovery_date = tns.loc[tns['sn_name'] == name, 'discovery_date'].values[0]
        elif name in osc['sn_name'].values:
            discovery_date = osc.loc[osc['sn_name'] == name, 'discovery_date(MJD)'].values[0]

    elif name in osc['sn_name'].values:
        max_date = osc.loc[osc['sn_name'] == name, 'maxdate(MJD)'].values[0]
        discovery_date = osc.loc[osc['sn_name'] == name, 'discovery_date(MJD)'].values[0]
    
    elif name in tns['sn_name'].values:
        max_date = 'unknown'
        discovery_date = tns.loc[tns['sn_name'] == name, 'discovery_date'].values[0]

    if str(max_date).lower() == 'nan': max_date = 'unknown'
    if str(discovery_date).lower() == 'nan': discovery_date = 'unknown'
    
    sn_list_data.append([name, sn_type, z, max_date, discovery_date])
#------------------------------------------------------------------------


#------------------------------------------------------------------------
# Writing to SNlist.txt

f1 = open('SNlist.txt', 'w')
line1 = f"{'# name':<25}\t{'type':<10}\t{'redshift':<10}\t{'max_date':<10}\t{'discovery_date':<10}"
line2 = f"{'#<U25':<25}\t{'<U10':<10}\t{'<10':<10}\t{'<10':<10}\t{'<10':<10}"

f1.write(line1 + '\n')
f1.write(line2 + '\n')

for row in sn_list_data:
    sn_name, sn_type, z, max_date, discovery_date = row
    z = str(z) if not pd.isna(z) else 'unknown'
    max_date = str(max_date) if not pd.isna(max_date) else 'unknown'
    discovery_date = str(discovery_date) if not pd.isna(discovery_date) else 'unknown'

    f1.write(f'{sn_name:<25}{sn_type:<10}{z:<10}{max_date:<20}{discovery_date:<20}\n')


