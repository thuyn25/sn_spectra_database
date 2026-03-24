'''
author:        thuyn25 <thuyn27@lsu.edu>
date:          2026-03-24 10:05:24
Copyright © YourCompanyName All rights reserved

Original version @author: Nikola Knezevic ASTRO DATA
'''

import datetime
import os
import requests
import json
import zipfile
import shutil
import csv
import sys
module_dir = os.path.abspath('../scripts/')
sys.path.append(module_dir)

from auxilary import clean_name

#------------------------------------------------------------------------
WISeREP                = "www.wiserep.org"

url_wis_spectra_search = "https://" + WISeREP + "/search/spectra"

# Example of specific parameter options related to the download itself:
# &num_page=250
# &format=tsv/csv/json
# &files_type=none/ascii/fits/all
# &personal_api_key=...
# &bot_api_key=...

personal_api_key       = "9454ce2c343c0da45e14f9ecd53daf0f49892aa2"     # MODIFY to your personal API key

# for User-Agent:
WIS_USER_NAME          = "thuyn27"                                      # MODIFY to your WIS sername
WIS_USER_ID            = "YOUR_USER_ID"                                 # MODIFY if available


# Specify the required parameters here
# Possible files type: &files_type=none | ascii | fits | all
# Possible metadata list format: &format=csv | tsv | json
# (In this example - all public type Ib/c's (and sub-types); metadata in CSV format; incl. ascii files.)
query_params           = "&public=yes&type[]=18/19/20"                        # this is to bulk download Sntype 
download_params        = "&num_page=250&format=csv&files_type=ascii"

parameters             = "?" + query_params+download_params + "&personal_api_key=" + personal_api_key

# url of wiserep spectra search (with parameters)
URL                    = url_wis_spectra_search + parameters

# external http errors
ext_http_errors       = [403, 500, 503]
err_msg               = ["Forbidden", "Internal Server Error: Something is broken", "Service Unavailable"]
#------------------------------------------------------------------------


#------------------------------------------------------------------------
def is_string_json(string):
    try:
        json_object = json.loads(string)
    except Exception:
        return False
    return json_object

def response_status(response):
    json_string = is_string_json(response.text)
    if json_string != False:
        status = "[ " + str(json_string['id_code']) + " - '" + json_string['id_message'] + "' ]"
    else:
        status_code = response.status_code
        if status_code == 200:
            status_msg = 'OK'
        elif status_code in ext_http_errors:
            status_msg = err_msg[ext_http_errors.index(status_code)]
        else:
            status_msg = 'Undocumented error'
        status = "[ " + str(status_code) + " - '" + status_msg + "' ]"
    return status

def print_response(response, page_num):
    status = response_status(response)
    stats = 'Page number ' + str(page_num) + ' | return code: ' + status        
    print (stats)
#------------------------------------------------------------------------


#------------------------------------------------------------------------
# current date and time
current_datetime = datetime.datetime.now()
current_date_time = current_datetime.strftime("%Y%m%d_%H%M%S")
# current_date_time = current_datetime.strftime("%Y%m%d")

# current working directory
# cwd = os.getcwd()
cwd = '../data/raw'

# current download folder
current_download_folder = os.path.join(cwd, "wiserep_raw_data_" + current_date_time)
os.makedirs(current_download_folder, exist_ok=True)

# marker and headers
wis_marker = 'wis_marker{"wis_id": "' + str(WIS_USER_ID) + '", "type": "user", "name": "' + WIS_USER_NAME + '"}'
headers = {'User-Agent': wis_marker}

# check file extension
if "format=tsv" in download_params:
    extension = ".tsv"
elif "format=csv" in download_params:
    extension = ".csv"
elif "format=json" in download_params:
    extension = ".json"
else:
    extension = ".txt"

# meta data list and file
META_DATA_LIST = []
META_DATA_FILE = os.path.join(cwd, "wiserep_metadata" + extension)

# page number
page_num = 0

# go trough every page
while True:
    # url for download
    url = URL + "&page=" + str(page_num)
    # send requests
    response = requests.post(url, headers = headers, stream = True)
    # chek if response status code is not 200
    if (response.status_code != 200):
        # if there are no more pages for download, don't print response, 
        # only print if response is something else
        if response.status_code != 404:
            print_response(response, page_num + 1)
        break 
    # print response
    print_response(response, page_num + 1)
    # download data
    file_name = 'wiserep_spectra.zip'
    file_path = os.path.join(current_download_folder, file_name)
    with open(file_path, 'wb') as f:
        for data in response:
            f.write(data)
    # unzip data
    zip_ref = zipfile.ZipFile(file_path, 'r')
    zip_ref.extractall(current_download_folder)
    zip_ref.close()
    # remove .zip file
    os.remove(file_path)            
    # take meta data file
    downloaded_files = os.listdir(current_download_folder)
    meta_data_file = os.path.join(current_download_folder, [e for e in downloaded_files if 'wiserep_spectra' in e][0])          
    # read meta data file
    f = open(meta_data_file,'r')
    meta_data_list = f.read().splitlines()
    f.close()
    # write this meta data list to the final meta data list
    if page_num == 0:
        META_DATA_LIST = META_DATA_LIST + meta_data_list
    else:
        META_DATA_LIST = META_DATA_LIST + meta_data_list[1:]         
    # increase page number 
    page_num = page_num + 1                 
    # remove meta data file
    os.remove(meta_data_file)

# write meta data list to file         
if META_DATA_LIST != []:
    f = open(META_DATA_FILE, 'w')
    for i in range(len(META_DATA_LIST)):
        if i == len(META_DATA_LIST) - 1:
            f.write(META_DATA_LIST[i])
        else:
            f.write(META_DATA_LIST[i] + '\n')
    f.close()
    print ("Wiserep data was successfully downloaded.")
    print ("Folder /wiserep_data_" + current_date_time + "/ containing the data was created.")
    print ("File spectra_" + current_date_time + extension + " was created.")
else:
    print ("There is no WISeREP data for the given parameters.")
    shutil.rmtree(current_download_folder)
#------------------------------------------------------------------------


#------------------------------------------------------------------------
print('Starting reformatting of spectra...')
downloaded_files = os.listdir(current_download_folder)
# print(current_download_folder, cwd)
meta_csv = os.path.join(cwd, 'wiserep_metadata.csv')

rename_path = os.path.join(cwd, "wiserep_rename_data_" + current_date_time)
os.makedirs(rename_path, exist_ok=True)

# 1. Open the final metadata file we just created
if os.path.exists(META_DATA_FILE):
    with open(META_DATA_FILE, mode='r', encoding='utf-8') as f:
        # Using DictReader to handle the "Ascii file" and "IAU name" columns
        reader = csv.DictReader(f)
        
        for row in reader:
            # Get the original filename from the metadata
            original_filename = row.get('Ascii file', '').strip()
            if not original_filename:
                continue
            print(original_filename)
            old_path = os.path.join(current_download_folder, original_filename)
            
            # Check if the file exists in the folder
            if os.path.exists(old_path):
                # Construct new filename: snname_UTCdate.dat
                iau_name = row.get('IAU name', '').strip()
                internal_names = row.get('Internal name/s', '').strip()
                raw_name = iau_name if iau_name else (internal_names.split(',')[0].split('/')[0] if internal_names else 'unknown')
                sn_name = raw_name.replace(" ", "").strip()
                # sn_name = original_filename.split('_')[0]
                clean_sn_name = clean_name(sn_name)
                # Extract YYYY-MM-DD from Obs-date
                full_obs_date = row.get('Obs-date', 'unknown')
                obs_date_only = full_obs_date.split()[0] if full_obs_date != 'unknown' else 'unknown'
                
                new_filename = f"{clean_sn_name}_{full_obs_date}.dat"
                new_path = os.path.join(rename_path, new_filename)
                
                # Read original content
                with open(old_path, 'r', encoding='utf-8', errors='ignore') as spec_file:
                    original_content = spec_file.read()

                # Write new file with the requested comment headers
                with open(new_path, 'w', encoding='utf-8') as out_file:
                    out_file.write(f"# time: {full_obs_date}\n")
                    out_file.write(f"# original filename: {original_filename}\n")
                    out_file.write(f"# observer: {row.get('Observer/s', 'unknown')}\n")
                    out_file.write(f"# redshift: {row.get('Redshift', 'unknown')}\n")
                    out_file.write(f"# Publication: {row.get('Publish', 'unknown')}\n")
                    # Combined Reducer and Source Group for credit
                    credit = f"{row.get('Reducer/s', 'unknown')}, {row.get('Source group', 'unknown')}"
                    out_file.write(f"# Credit: {credit}\n")
                    out_file.write(original_content)

                # Remove the original file with the long/complex name
                if old_path != new_path:
                    os.remove(old_path)

    print(f"Success! Spectra in '{current_download_folder}' are now reformatted for post-processing.")
else:
    print(f"Error: {META_DATA_FILE} not found. Reformatting skipped.")
# --- END OF AUTOMATIC REFORMATTING ---