import requests
import json
import logging

YESWEHACK_PROGRAMS_ENDPOINT = "https://api.yeswehack.com/programs"
YESWEHACK_PROGRAM_BASE_ENDPOINT = "https://api.yeswehack.com/programs/"

def yeswehack_programs(api_token, vdp, hidden, categories):
    program_info = get_all_programs_scope(api_token, vdp, hidden, categories)
    return program_info

def get_category_id(input_str):
    categories = {
        "url": ["web-application", "api", "ip-address"],
        "mobile": ["mobile-application", "mobile-application-android", "mobile-application-ios"],
        "android": ["mobile-application-android"],
        "apple": ["mobile-application-ios"],
        "other": ["other"],
        "executable": ["application"],
        "all": ["web-application", "api", "ip-address", "mobile-application", "mobile-application-android", "mobile-application-ios", "other", "application"],
    }

    selected_category = categories.get(input_str.lower())
    if not selected_category:
        raise ValueError("Invalid category")
    return selected_category

def get_program_scope(token, company_slug, categories):
    url = YESWEHACK_PROGRAM_BASE_ENDPOINT + company_slug
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.fatal(f"HTTP request failed: {e}")
        return None

    data = response.json()
    scopes = data['scopes']

    pdata = {'InScope': []}

    selected_cat_ids = get_category_id(categories)
    for scope in scopes:
        if scope['scope_type'] in selected_cat_ids:
            pdata["InScope"].append({
                "Target": scope["scope"],
                "Category": scope["scope_type"],
                "Asset": scope["asset_value"],
            })
    return pdata

def get_all_programs_scope(token, bbp_only, pvt_only, categories):
    programs = []
    page = 1
    nb_pages = 2

    while page <= nb_pages:
        try:
            response = requests.get(f"{YESWEHACK_PROGRAMS_ENDPOINT}?page={page}", headers={"Authorization": f"Bearer {token}"})
            response.raise_for_status()
        except requests.RequestException as e:
            logging.fatal(f"HTTP request failed: {e}")
            return []

        data = response.json()
        items = data['items']
        pagination = data['pagination']
        nb_pages = pagination['nb_pages']

        for item in items:
            if not pvt_only or (pvt_only and not item['public']):
                if not bbp_only or (bbp_only and item['bounty']):
                    pdata = get_program_scope(token, item['slug'], categories)
                    pdata["Title"] = item['title']
                    pdata["Program Handle"] = item['slug']
                    pdata["Program Type"] = ("Public" if item["public"] else "False")
                    # pdata["Creation Date"] = item['event']
                    pdata["Bounty"] = item['bounty']
                    if item['bounty']:
                        pdata["Bounty Minimum"] = item['bounty_reward_min']
                        pdata["Bounty Maximum"] = item['bounty_reward_max']
                        # pdata["Reward Grid Default"] = item.get('reward_grid_default', {})
                    if pdata:
                        programs.append(pdata)

        page += 1

    return programs

def yeswehack_wildcard_programs(token, vdp, hidden, categories):
    programs = []
    page = 1
    nb_pages = 2

    while page <= nb_pages:
        try:
            response = requests.get(f"{YESWEHACK_PROGRAMS_ENDPOINT}?page={page}", headers={"Authorization": f"Bearer {token}"})
            response.raise_for_status()
        except requests.RequestException as e:
            logging.fatal(f"HTTP request failed: {e}")
            return []

        data = response.json()
        items = data['items']
        pagination = data['pagination']
        nb_pages = pagination['nb_pages']

        for item in items:
            if not hidden or (hidden and not item['public']):
                if not vdp or (vdp and item['bounty']):
                    scope_data = get_program_scope(token, item['slug'], categories)
                    if scope_data and scope_data['InScope']:
                        pdata = {
                            "Title": item['title'],
                            "Bounty": item['bounty'],
                            "Program Type": ("Public" if item["public"] else "False")
                        }
                        if item['bounty']:
                            pdata["Bounty Minimum"] = item['bounty_reward_min']
                            pdata["Bounty Maximum"] = item['bounty_reward_max']
                        pdata['InScope'] = scope_data['InScope']
                        programs.append(pdata)

        page += 1

    return programs
