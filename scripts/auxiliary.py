'''
author:        thuyn25 <thuyn27@lsu.edu>
date:          2026-03-24 11:03:06
Copyright © YourCompanyName All rights reserved
'''
import re
import json

def clean_name(name: str):
    new_name = ""
    cleaned_name = name.strip()
    if len(cleaned_name) >= 2 and cleaned_name[0].lower() == "s" and cleaned_name[1].lower() == 'n':
        new_name = cleaned_name[2:]
        new_name = new_name.strip()
    else:
        new_name = name
    return new_name


def clean_osc_sn_type(t):
    """Clean SN type string for safe directory naming."""
    if t is None:
        return None
    
    # Replace whitespace with underscore
    t = re.sub(r"\s+", "_", t)

    # Replace ? with Q
    t = t.replace("?", "Q")
    
    t = t.replace("/", "_")

    # Remove hyphens
    t = t.replace("-", "")

    # If starts with digit, prefix with 'n'
    if re.match(r"^\d", t):
        t = "n" + t

    return t


def load_json_safe(file_path):
    try: 
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"Skipping {file_path}: Failed to load JSON. {e}")
        return None

def normalize_name(name):   # for matching sn_event
    if not isinstance(name, str): return ""
    # Remove all non-alphanumeric characters and lowercase
    return re.sub(r'[^a-zA-Z0-9]', '', name)