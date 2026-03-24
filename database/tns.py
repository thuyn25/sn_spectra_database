'''
author:        thuyn25 <thuyn27@lsu.edu>
date:          2026-03-24 11:28:58

Credit: Nikola Knezevic ASTRO DATA
'''

import datetime
import os
import requests
import json
import time


#--------------------------------------------------- PARAMETERS --------------------------------------------------#
tns = "www.wis-tns.org" # production
# tns = "sandbox.wis-tns.org" # sandbox

url_tns_search = "https://" + tns + "/search"

tns_bot_id = "197883"               # MODIFY 
tns_bot_name = "LSU_Bot"            # MODIFY 

tns_user_id = "4221"                # MODIFY 
tns_user_name = "thuyn27"           # MODIFY 
user_or_bot = "user"                # MODIFY 

# List of all possible parameters ("keys") for building tns search url (NO CHANGE)
url_parameters = [
                  "reported_within_last_value", 
                  "reported_within_last_units", 
                  "unclassified_at", 
                  "classified_sne", 
                  "classified_tde", 
                  "include_frb", 
                  "name", 
                  "name_like", 
                  "isTNS_AT", 
                  "public", 
                  "ra", 
                  "decl", 
                  "radius", 
                  "coords_unit", 
                  "reporting_groupid[]",
                  "groupid[]", 
                  "classifier_groupid[]", 
                  "objtype[]", 
                  "at_type[]", 
                  "discovery_date_start",
                  "ddiscovery_date_end",  
                  "discovery_mag_min", 
                  "discovery_mag_max", 
                  "internal_name", 
                  "discoverer", 
                  "classifier", 
                  "spectra_count", 
                  "redshift_min", 
                  "redshift_max", 
                  "hostname", 
                  "ext_catid", 
                  "ra_range_min", 
                  "ra_range_max", 
                  "decl_range_min", 
                  "decl_range_max", 
                  "discovery_instrument[]", 
                  "classification_instrument[]", 
                  "associated_groups[]", 
                  "official_discovery", 
                  "official_classification",
                  "auto_classification_algorithm", 
                  "auto_classification_objtypeid", 
                  "auto_classification_prob", 
                  "at_rep_remarks", 
                  "class_rep_remarks",
                  "frb_repeat", 
                  "frb_repeater_of_objid", 
                  "frb_measured_redshift", 
                  "frb_dm_range_min", 
                  "frb_dm_range_max", 
                  "frb_rm_range_min", 
                  "frb_rm_range_max", 
                  "frb_snr_range_min", 
                  "frb_snr_range_max", 
                  "frb_flux_range_min", 
                  "frb_flux_range_max", 
                  "format", 
                  "num_page"
                 ]

# Here you put "key":"value" pairs for building your tns search url 
build_url_parameters = {}

# merge_to_single_file  = "Here put 0 (no) or 1 (yes) to merge retrieved entries into single csv/tsv file."
merge_to_single_file = "1"

ext_http_errors = [403, 500, 503]
err_msg = ["Forbidden", "Internal Server Error: Something is broken", "Service Unavailable"]
#-----------------------------------------------------------------------------------------------------------------#

#-----------------------------------------------------------------------------------------------------------------#
def set_bot_tns_marker(bot_id, bot_name):
    tns_marker = 'tns_marker{"tns_id": "' + str(bot_id) + '", "type": "bot", "name": "' + bot_name + '"}'
    return tns_marker

def set_user_tns_marker(user_id, user_name):
    tns_marker = 'tns_marker{"tns_id": "' + str(user_id) + '", "type": "user", "name": "' + user_name + '"}'
    return tns_marker

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
    if response.status_code == 200:
        if(response.headers.get('x-rate-limit-limit') != None):
            stats = 'Page number ' + str(page_num) + ' | return code: ' + status + \
                    ' | Total Rate-Limit: ' + str(response.headers.get('x-rate-limit-limit')) + \
                    ' | Remaining: ' + str(response.headers.get('x-rate-limit-remaining')) + \
                    ' | Reset: ' + str(response.headers.get('x-rate-limit-reset') + ' sec')   
            print (stats)       
        else:         
            print ("An error occurred in the rate limits.")
            print ("There is no 'x-rate-limit-limit' keywords in the response.headers function.")
            print ("Please check what went wrong.\n")
            return False
    else:
        stats = 'Page number ' + str(page_num) + ' | return code: ' + status
        print (stats)
    return

def get_reset_time(response):
    # If any of the '...-remaining' values is zero, return the reset time
    for name in response.headers:
        value = response.headers.get(name)
        if name.endswith('-remaining') and value == '0':
            return int(response.headers.get(name.replace('remaining', 'reset')))
    return None

# Function for searching tns with specified url parameters
def search_tns(url_par, file_dir, user_bot, bot_id, bot_name, user_id, user_name):
    # Extract keywords and values from url parameters
    keywords = list(url_par.keys())
    values = list(url_par.values())
    # Flag for checking if url is with correct keywords
    wrong_url = False
    # Check if keywords are correct
    for i in range(len(keywords)):
        if keywords[i] not in url_parameters:
            print ("Unknown url keyword '" + keywords[i] + "'\n")
            wrong_url = True
    # Check flag
    if wrong_url == True:
        print ("TNS search url is not in the correct format.\n")
    # Else, if everything is correct
    else:
        # Current date and time
        current_datetime = datetime.datetime.now()
        # current_date_time = current_datetime.strftime("%Y%m%d_%H%M%S")  
        current_date_time = current_datetime.strftime("%Y%m%d")  
        # Create searched results folder
        tns_search_folder = "tns_search_data_" + current_date_time
        tns_search_folder_path = os.path.join(file_dir, tns_search_folder)
        os.makedirs(tns_search_folder_path, exist_ok=True)
        print ("TNS searched data folder /" + tns_search_folder + "/ is successfully created.\n")            
        # File containing searched data
        if "format" in keywords:
            extension = "." + url_par["format"]
        else:
            extension = ".txt"
        # Build tns search url
        url_param = ['&' + x + '=' + y for x, y in zip(keywords, values)]
        tns_search_url = url_tns_search + '?' + "".join(url_param)
        # Page number
        page_num = 0
        # Searched data
        searched_data = []
        # Go trough every page
        while True:
            # Url for download
            url = tns_search_url + "&page=" + str(page_num)
            # TNS marker
            if user_bot == 'bot':
                tns_marker = set_bot_tns_marker(bot_id, bot_name)
            else:
                tns_marker = set_user_tns_marker(user_id, user_name)
            # Headers
            headers = {'User-Agent': tns_marker}
            # Downloading file using request module
            response = requests.post(url, headers=headers, stream=True) 
            # Chek if response status code is not 200, or if returned data is empty
            if (response.status_code != 200) or (len((response.text).splitlines()) <= 1):
                if response.status_code != 200:
                    print ("Sending download search request for page num " + str(page_num + 1) + "...")
                    # Print status code of the response
                    print_response(response, page_num + 1)        
                break
            print ("Sending download search request for page num " + str(page_num + 1) + "...")
            # Print status code of the response
            r = print_response(response, page_num + 1)
            if r == False:
                break
            # Get data
            data = (response.text).splitlines()
            # Create file per page
            if merge_to_single_file == 0:
                tns_search_f = "tns_search_data_" + current_date_time + "_part_" + str(page_num + 1) + extension
                tns_search_f_path = os.path.join(tns_search_folder_path, tns_search_f)
                f = open(tns_search_f_path, 'w')
                for el in data:
                    f.write(el + '\n')
                f.close() 
                if len(data) > 2:
                    print ("File '" + tns_search_f + "' (containing " + str(len(data) - 1) +\
                           " rows) is successfully created.\n")                     
                else: 
                    print ("File '" + tns_search_f + "' (containing 1 row) is successfully created.\n")
            else:
                print ("")
            # Add to searched data
            if page_num == 0:
                searched_data.append(data)
            else:
                searched_data.append(data[1:])
            # Check reset time
            reset = get_reset_time(response)
            if reset != None:
                # Sleeping for reset + 1 sec
                print("\nSleep for " + str(reset + 1) + " sec and then continue...\n") 
                time.sleep(reset + 1)
            # Increase page num
            page_num = page_num + 1
        # If there is searched data, write to file
        if searched_data != []:            
            searched_data = [j for i in searched_data for j in i]
            if merge_to_single_file == 1:              
                tns_search_file = "tns_metadata" + extension
                tns_search_file_path = os.path.join(file_dir, tns_search_file)
                f = open(tns_search_file_path, 'w')
                for el in searched_data:
                    f.write(el + '\n')
                f.close()
                if len(searched_data) > 2:
                    print ("\nTNS searched data returned " + str(len(searched_data) - 1) + " rows. File '" + \
                           tns_search_file + "' is successfully created.\n")
                else: 
                    print ("\nTNS searched data returned 1 row. File '" + tns_search_file + "' is successfully created.\n")            
            else:
                if len(searched_data) > 2:
                    print ("TNS searched data returned " + str(len(searched_data) - 1) + " rows in total.\n")
                else: 
                    print ("TNS searched data returned 1 row in total.\n")
        else: 
            print ("TNS searched data returned empty list. No file(s) created.\n")
            # Remove empty folder
            os.rmdir(tns_search_folder_path)
            print ("Folder /" + tns_search_folder + "/ is removed.\n")
#-----------------------------------------------------------------------------------------------------------------#


#--------------------------------------------------- EXECUTION ----------------------------------------------------#
cwd  = '../data/raw'
csv_tsv_file_dir = os.path.join(cwd)

# Comment/Uncomment sections for testing the various examples:

build_url_parameters = {"reported_within_last_value" : "5", "reported_within_last_units" : "years", 
                        "classified_sne" : "1", "objtype[]": "18,19,20", "format" : "csv", "num_page" : "20"}
merge_to_single_file = 1
search_tns(build_url_parameters, csv_tsv_file_dir, user_or_bot, tns_bot_id, tns_bot_name, tns_user_id, tns_user_name)
