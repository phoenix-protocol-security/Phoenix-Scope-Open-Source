import requests
import json
import time
import logging
from datetime import datetime

def intigriti_programs(api_token, vdp, hidden, wildcard):
    program_info = get_all_programs_scope(api_token, vdp, hidden, "all", wildcard)
    return program_info

def get_category_id(input_str):
    categories = {
        "url": [1],
        "cidr": [4],
        "mobile": [2, 3],
        "android": [2],
        "apple": [3],
        "device": [5],
        "other": [6],
        "all": [1, 2, 3, 4, 5, 6],
    }

    selected_category = categories.get(input_str.lower())
    if not selected_category:
        raise ValueError("Invalid category")
    return selected_category

def get_program_scope(token, program_id, categories, wildcard):
    url = f"https://api.intigriti.com/external/researcher/v1/programs/{program_id}"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
    except requests.HTTPError as e:
        # logging.fatal("HTTP request failed: ", e)
        return None

    if "Request blocked" in res.text:
        logging.info("Rate limited. Retrying...")
        time.sleep(2)
        return get_program_scope(token, program_id, categories)

    content_array = json.loads(res.text)["domains"]["content"]
    res_json = json.loads(res.text)
    program_handle = res_json["handle"]
    program_name = res_json["name"]
    created_date = datetime.utcfromtimestamp(res_json["rulesOfEngagement"].get("createdAt", 0)).strftime('%d/%m/%Y') if res_json.get("rulesOfEngagement") else "N/A"


    if wildcard:
        pdata = {"InScope": []}
        for item in content_array:
            endpoint = item["endpoint"]
            category_id = item["type"]["id"]
            category_value = item["type"]["value"]
            tier_id = item["tier"]["id"]
            # description = item.get("description", "")

            # if description:
            #     description = description.replace("\n", "  ")

            # Check if the endpoint contains a wildcard
            if "*." in endpoint:
                scope_entry = {
                    # "Name": program_name,
                    # "Handle": program_handle,
                    "Target": endpoint,
                    "Category": category_value
                }

                # Add description only if it's not empty
                # if description:
                #     scope_entry["Description"] = description

                if tier_id != 5 and int(category_id) in get_category_id(categories):
                    pdata["Program Name"] = program_name
                    pdata["Program Handle"] = program_handle
                    pdata["Created Date"] = created_date
                    pdata["InScope"].append(scope_entry)
        return pdata
    else:
        pdata = {"InScope": []}
        for item in content_array:
            endpoint = item["endpoint"]
            category_id = item["type"]["id"]
            category_value = item["type"]["value"]
            tier_id = item["tier"]["id"]
            # description = item.get("description", "")

            # if description:
            #     description = description.replace("\n", "  ")

            scope_entry = {
                # "Name": program_name,
                # "Handle": program_handle,
                "Target": endpoint,
                "Category": category_value
            }
            # Add description only if it's not empty
            # if description:
            #     scope_entry["Description"] = description

            if tier_id != 5:
                if int(category_id) in get_category_id(categories):
                    pdata["Program Name"] = program_name
                    pdata["Program Handle"] = program_handle
                    pdata["Created Date"] = created_date
                    pdata["InScope"].append(scope_entry)
            # else:
            #     pdata["OutOfScope"].append(scope_entry)
            # else:
            #     if include_oos:
            #         pdata["OutOfScope"].append({
            #             "Target": endpoint,
            #             "Description": description,
            #             "Category": category_value
            #         })
        return pdata

def get_all_programs_scope(token, bbp_only, pvt_only, categories, wildcard):
    offset = 0
    limit = 50
    total = 0
    programs = []

    while True:
        url = f"https://api.intigriti.com/external/researcher/v1/programs?limit={limit}&offset={offset}"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            res = requests.get(url, headers=headers)
            res.raise_for_status()
        except requests.HTTPError as e:
            # logging.fatal("HTTP request failed: ", e)
            return []

        body = json.loads(res.text)

        if offset == 0:
            total = body["maxCount"]
            logging.info("Total Programs available: ", total)

        records = body["records"]
        for record in records:
            id = record["id"]
            handle = record["handle"]
            max_bounty = record.get("maxBounty", {}).get("value", 0)
            confidentiality_level = record["confidentialityLevel"]["id"]
            # created_date = record["rulesOfEngagement"]["createdAt"]

            if (pvt_only and confidentiality_level != 4) or not pvt_only:
                if (bbp_only or max_bounty != 0) or not bbp_only:
                    pdata = get_program_scope(token, id, categories, wildcard)
                    if pdata and "InScope" in pdata and pdata["InScope"]:
                        if any([bbp_only, pvt_only, categories, wildcard]):
                            pdata["MaxBounty"] = 0 if bbp_only else max_bounty
                        pdata["Program Type"] = record["confidentialityLevel"]["value"]
                        print(f"{handle}:{max_bounty}")
                        programs.append(pdata)

        offset += len(records)
        if offset >= total:
            break

    return programs

def get_bounty_programs_scope(token, categories, bbp_only, pvt_only):
    offset = 0
    limit = 50
    total = 0
    programs = []

    while True:
        url = f"https://api.intigriti.com/external/researcher/v1/programs?limit={limit}&offset={offset}"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            res = requests.get(url, headers=headers)
            res.raise_for_status()
        except requests.HTTPError as e:
            logging.fatal(f"HTTP request failed: {e}")
            return []

        body = json.loads(res.text)

        if offset == 0:
            total = body["maxCount"]
            logging.info(f"Total Programs available: {total}")

        records = body["records"]
        for record in records:
            id = record["id"]
            handle = record["handle"]
            max_bounty = record.get("maxBounty", {}).get("value", 0)
            confidentiality_level = record["confidentialityLevel"]["id"]

            if (pvt_only and confidentiality_level != 4) or not pvt_only:
                if (bbp_only or max_bounty != 0) or not bbp_only:
                    pdata = get_program_scope(token, id, categories, False)
                    if pdata is not None and max_bounty > 0:
                        pdata["MaxBounty"] = max_bounty
                        programs.append(pdata)

        offset += len(records)
        if offset >= total:
            break

    return programs

def get_wildcard_programs_scope(token, categories, bbp_only, pvt_only):
    offset = 0
    limit = 50
    total = 0
    programs = []

    while True:
        url = f"https://api.intigriti.com/external/researcher/v1/programs?limit={limit}&offset={offset}"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            res = requests.get(url, headers=headers)
            res.raise_for_status()
        except requests.HTTPError as e:
            logging.fatal(f"HTTP request failed: {e}")
            return []

        body = json.loads(res.text)

        if offset == 0:
            total = body["maxCount"]
            logging.info(f"Total Programs available: {total}")

        records = body["records"]
        for record in records:
            id = record["id"]
            handle = record["handle"]
            max_bounty = record.get("maxBounty", {}).get("value", 0)
            confidentiality_level = record["confidentialityLevel"]["id"]

            if (pvt_only and confidentiality_level != 4) or not pvt_only:
                if (bbp_only or max_bounty != 0) or not bbp_only:
                    pdata = get_program_scope(token, id, categories, True)
                    if pdata and pdata["InScope"]:
                        pdata["MaxBounty"] = max_bounty
                        programs.append(pdata)

        offset += len(records)
        if offset >= total:
            break

    return programs
