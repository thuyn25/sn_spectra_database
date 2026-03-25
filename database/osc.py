'''
author:        thuyn25 <thuyn27@lsu.edu>
date:          2026-03-24 11:43:29

# you must have osc_database downloaded to your machine
'''

import os
import json
import numpy as np
import pandas as pd
import sys
import re
from astropy.time import Time   # converting regular time format to MJD
import datetime

module_dir = os.path.abspath('../scripts/')
sys.path.append(module_dir)

from auxiliary import clean_name, load_json_safe, clean_osc_sn_type

#--------------------------------------------------- PARAMETERS --------------------------------------------------#
current_datetime = datetime.datetime.now()
# current_date_time = current_datetime.strftime("%Y%m%d_%H%M%S")
current_date_time = current_datetime.strftime("%Y%m%d")

cwd =  '../data/raw'
outpath = os.path.join(cwd, 'osc_raw_data_' + current_date_time)
os.makedirs(outpath, exist_ok=True)

input_master = '/Users/beehuynh/Developer/test_suites/OSC_database/'    # './OSC_master/' need to modify before pushing to GitHub
# sn_subfolders = [
#     'sne-pre-1990-master', 'sne-1990-1999-master', 'sne-2000-2004-master',
#     'sne-2005-2009-master', 'sne-2010-2014-master', 
#     'sne-2015-2019-master', 'sne-2020-2024-main']

sn_subfolders = [ 'sne-2000-2004-master',
    'sne-2005-2009-master', 'sne-2010-2014-master', 
    'sne-2015-2019-master', 'sne-2020-2024-main']
sn_types = ['SLSNI', 'SLSNII', 'SLSNR']
#-----------------------------------------------------------------------------------------------------------------#


#-----------------------------------------------------------------------------------------------------------------#
def extract_metadata(data, sn_name):
    """Extract Sn type, redshifts, discoverdate, maxdate, and luminosity distance (lumdist)"""
    def get_last_value(entry_list, default=np.nan):
        """Return the last 'value' field from a list of dicts, or default."""
        if entry_list:
            val = entry_list[-1].get("value")
            try:
                return float(val) if isinstance(default, float) else str(val)
            except (TypeError, ValueError):
                return default
        return default
    
    claim = data.get(sn_name, {}).get("claimedtype", [])
    raw_sn_type = claim[-1].get("value") if claim else None
    sn_type = clean_osc_sn_type(raw_sn_type)
    
    if sn_type == 'Candidate' and sn_type == None:
        print(f'Skipping Candidate and none SN type')
        return
    z = get_last_value(data.get(sn_name, {}).get("redshift", []), default=np.nan)
    
    d_L = get_last_value(data.get(sn_name, {}).get("lumdist", []), default=np.nan)

    discover_date_str = get_last_value(data.get(sn_name, {}).get("discoverdate", []), default=None)
    
    disdate_mjd = np.nan
    disdate = 'unknown'
    maxdate = 'unknown'
    if discover_date_str:
        try:
            # disdate_mjd = float(ymd_to_mjd(discover_date_str))
            disdate = discover_date_str.replace('/', '-')
        except Exception:
            # disdate_mjd = np.nan
            disdate = 'unknown'

    maxdate_str = get_last_value(data.get(sn_name, {}).get("maxdate", []), default=None)
    
    maxdate_mjd = np.nan
    if maxdate_str:
        try:
            # maxdate_mjd = float(ymd_to_mjd(maxdate_str))
            maxdate = maxdate_str.replace('/', '-')
        except Exception:
            # maxdate_mjd = np.nan
            maxdate = 'unknown'

    return sn_type, z, d_L, disdate, maxdate

def process_phot_file(data, sn_name, sn_type, z, d_L, disdate_mjd, maxdate_mjd, counter_flag=False):
    # --- 1. Extract raw light curve points (lc_data) ---
    lc_data = []
    photometry = data.get(sn_name, {}).get('photometry', [])

    for entry in photometry:
        time = entry.get('time')
        mag = entry.get('magnitude')
        band = entry.get('band')
        err = entry.get('e_magnitude')
        # print(time, mag)
        # if isinstance(time, list):
        #     time = time[0] if time else None
        # if isinstance(mag, list):
        #     mag = mag[0] if mag else None

        if time is not None and mag is not None and band is not None:
            try:
                lc_data.append([
                    sn_name, sn_type, z, d_L, disdate_mjd, maxdate_mjd, float(time), band, float(mag), float(err) if err is not None else np.nan
                ])
            except (TypeError, ValueError):
                continue

    if not lc_data:
        # print(f"Warning: No valid photometry data found for '{sn_name}'.")
        return None, False
    else: 
        # photometry_counters[sn_type] = photometry_counters.get(sn_type, 0) + 1
        counter_flag = True
        # print(f"Processing photometry for {file} in process_sn_file.")
    # --- 2. Pivot to Time-Series DataFrame (Replacing NumPy Tab) ---

    lc = np.array(lc_data)

    dates = np.unique(lc[:,6])  # time colume index 6
    filters = sorted(np.unique(lc[:,7]).tolist())  #band column index 7

    df_lc_raw = pd.DataFrame(lc_data, columns=['sn_name', 'sn_type', 'redshift', 'd_L', 'discover_date', 'maxdate', 'time', 'band', 'magnitude', 'err'])

    # Ensure float types for numerical columns before pivot
    df_lc_raw['time'] = pd.to_numeric(df_lc_raw['time'], errors='coerce')
    df_lc_raw['magnitude'] = pd.to_numeric(df_lc_raw['magnitude'], errors='coerce')
    df_lc_raw['err'] = pd.to_numeric(df_lc_raw['err'], errors='coerce')

    df_mag = df_lc_raw.pivot_table(index='time', columns='band', values='magnitude', aggfunc='first')
    df_err = df_lc_raw.pivot_table(index='time', columns='band', values='err', aggfunc='first')

    combined_cols = []
    for f in filters:
        combined_cols.extend([f, f + '_err'])
    
    df_ts = pd.DataFrame(index=df_mag.index)
    for f in filters:
        # Fill NaN if the filter is missing in the SN
        df_ts[f] = df_mag.get(f, pd.Series(np.nan, index=df_mag.index))
        df_ts[f + '_err'] = df_err.get(f, pd.Series(np.nan, index=df_err.index))
    
    # add metadata back to df_ts
    df_ts['sn_name'] = sn_name
    df_ts['sn_type'] = sn_type
    df_ts['redshift'] = z

    final_cols = ['sn_name', 'sn_type', 'redshift'] + [col for col in df_ts.columns if col not in ['sn_name', 'sn_type', 'redshift']]
    df_ts = df_ts[final_cols]

    df_ts = df_ts.reset_index().rename(columns={'index': 'time'})

    # normalized time wrt maxdate
    if maxdate_mjd is not None and not np.isnan(maxdate_mjd):
        df_ts['norm_time'] = df_ts['time'] - maxdate_mjd
    else:
        df_ts['norm_time'] = np.nan
    
    return df_ts, counter_flag

def process_spec_file(data, sn_name):
    # This list will hold a dictionary for every spectrum we successfully save
    extracted_rows = []
    
    if data is not None:
        # Get the "global" SN metadata once per file
        sn_type, z_global, d_L, disdate, maxdate = extract_metadata(data, sn_name)

        # Only process if it's one of your target SLSN types
        if sn_type in sn_types:
            if 'spectra' in data[sn_name] and data[sn_name]['spectra']:
                
                for i in range(len(data[sn_name]['spectra'])):
                    spec_entry = data[sn_name]['spectra'][i]
                    
                    try:
                        # --- 1. DATA PROCESSING (KEPT EXACTLY THE SAME) ---
                        test = np.array(spec_entry['data'])
                        test2 = np.vectorize(float)(test)

                        # --- 2. METADATA EXTRACTION ---
                        f_name_orig = spec_entry.get('filename', 'unknown')
                        obs = spec_entry.get('observer', 'unknown')
                        spec_z = spec_entry.get('redshift', 'unknown')
                        u_flux = spec_entry.get('u_fluxes', 'unknown')
                        u_wave = spec_entry.get('u_wavelengths', 'unknown')
                        
                        time_mjd = spec_entry.get('time', None)
                        if time_mjd:
                            date_obj = Time(time_mjd, format='mjd', scale='utc')
                            utc_str = date_obj.to_value('iso')
                            date_part = utc_str.split(' ')[0]
                        else:
                            utc_str = 'unknown'
                            date_part = 'no_date'

                        clean_sn_name = clean_name(sn_name)
                        basename = f"{clean_sn_name}_{date_part}"
                        spec_name = f"{basename}.dat"
                        specpath = os.path.join(outpath, spec_name)
                        counter = 1
                        while os.path.exists(specpath):
                            spec_name = f"{basename}_v{counter}.dat"
                            specpath = os.path.join(outpath, spec_name)
                            counter += 1
                        
                        if counter > 1:
                            print(f"Collision resolve: {spec_name} (needed {counter-1} attempts).")


                        # --- 3. SAVE .DAT FILE (KEPT EXACTLY THE SAME) ---
                        header_text = (
                            f"time: {utc_str}\n"
                            f"filename: {f_name_orig}\n"
                            f"observer: {obs}\n"
                            f"redshift: {spec_z}\n"
                            f"u_fluxes: {u_flux}\n"
                            f"u_wavelengths: {u_wave}"
                        )
                        np.savetxt(specpath, test2, fmt='%.7e', delimiter='\t', header=header_text)

                        # --- 4. CREATE CSV ROW ENTRY ---
                        # We combine the SN-level info with this specific spectrum's info
                        row = {
                            'sn_name': clean_sn_name,
                            'sn_type': sn_type,
                            'redshift': z_global,
                            'lum_dist': d_L,
                            'discovery_date(MJD)': disdate,
                            'maxdate(MJD)': maxdate,
                            'utc_str': utc_str,''
                            'fname_spec': spec_name,
                            'fname_spec_orig': f_name_orig,  # The .dat filename we just created
                            'observer': obs,
                            'spec_redshift': spec_z,
                            'unit_flux': u_flux,
                            'unit_wave': u_wave
                        }
                        extracted_rows.append(row)

                    except Exception as e:
                        print(f'Spectrum index {i} for {sn_name} failed: {e}')
                        
    return extracted_rows
#-----------------------------------------------------------------------------------------------------------------#


#--------------------------------------------------- EXECUTION ----------------------------------------------------#
all_slsn_metadata = []
slsn_type_counts = {}
slsn_spec_counts = {}
total_files = 0

for folder in sn_subfolders:
    input_path = os.path.join(input_master, folder)
    if not os.path.isdir(input_path):
        print(f'Warning: Dorectory not found: {input_path}')
        continue

    filenames = [f for f in os.listdir(input_path) if os.path.isfile(os.path.join(input_path, f))]
    total_files += len(filenames)   #TRACKING COUNTS of events

    for file in filenames:
        sn_name = file.split('.')[0]
        file_path = os.path.join(input_path, file)

        sn_data = load_json_safe(file_path)
        
        if sn_data is None:
            print(f'Data in file {file} is None')
            continue
        sn_type, z, d_L, disdate_mjd, maxdate_mjd = extract_metadata(sn_data, sn_name)
        
        # Saving spectra files
        new_rows = process_spec_file(sn_data, sn_name)
        if new_rows:
            # .extend adds all dictionaries in the list to our master list
            all_slsn_metadata.extend(new_rows)
            
            # Count the SN event type once per JSON file
            stype = new_rows[0]['sn_type']
            slsn_spec_counts[stype] = slsn_spec_counts.get(stype, 0) + 1

df_slsn_metadata = pd.DataFrame(all_slsn_metadata)
df_slsn_metadata.to_csv(f'{cwd}/osc_metadata.csv', index=False)
print('slsn_type_counts:', slsn_type_counts)
print('slsn_spec_counts:', slsn_spec_counts)
