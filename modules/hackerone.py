import requests
import json
import sys
from datetime import datetime, timedelta
import dateutil.parser
import pytz
from concurrent.futures import ThreadPoolExecutor, as_completed


def hackerone(username, api_token, private, bounty, wildcards, mobile_app, single_domain):
    program_json_output = get_h1_programs(username, api_token, private, bounty, wildcards, mobile_app, single_domain)
    return program_json_output

def fetch_programs_page(page_number, auth):
    response = requests.get(f"https://api.hackerone.com/v1/hackers/programs?page[size]=100&page[number]={page_number}", auth=auth)
    if response.status_code not in [200, 404]:
        print(f"Request returned {response.status_code}!")
        sys.exit()

    data = response.json()

    if response.status_code == 404 or len(data["data"]) == 0:
        return []

    return data["data"]

def hackerone_wildcards(username, api_token):
    auth = (username, api_token)

    max_results = 200

    page_number = 0
    programs_list = []

    while True:
        response = requests.get(f"https://api.hackerone.com/v1/hackers/programs?page[size]=100&page[number]={page_number}", auth=auth)

        if response.status_code not in [200, 404]:
            print(f"Request returned {response.status_code}!")
            sys.exit()

        data = response.json()

        if response.status_code == 404 or len(data["data"]) == 0:
            break

        programs_list.extend(data["data"])
        page_number += 1

    # Reversing the list
    programs_list = programs_list[::-1]

    count = 0
    json_output = []

    wildcard = True
    url = False
    mobile_app = False

    for program in programs_list:
        if count == max_results:
            break

        program_handle = program["attributes"]["handle"]
        program_INscope, program_OUTscope = get_wildcard_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
        if program_INscope or program_OUTscope:
            INscope_info = program_INscope
            OUTscope_info = program_OUTscope

            program_info = {
                    "Program Name": program["attributes"]["name"],
                    "In Scope": INscope_info
            }
            json_output.append(program_info)
        count +=1

    return json_output

def get_wildcard_program_scope(program_handle, username, api_token, wildcard, url, mobile_app):
    auth = (username, api_token)

    # Constructing the API request URL
    request_url = f"https://api.hackerone.com/v1/hackers/programs/{program_handle}/structured_scopes?page%5Bsize%5D=100"

    # Making the GET request to the HackerOne API for fetching the program scope with the page size to max=100.
    r = requests.get(request_url, auth=auth)
    if r.status_code != 200:
        print(f"Request returned {r.status_code}!")
        sys.exit()

    data = r.json()

    in_scope_list = []
    out_of_scope_list = []
    for scope in data["data"]:
        asset_type = scope["attributes"]["asset_type"]

        # For WILDCARD Scope
        if (wildcard and asset_type == "WILDCARD"):
            scope_info = {
                "Asset": scope["attributes"]["asset_identifier"]
            }

            # Adding scope to the appropriate list
            if scope["attributes"]["eligible_for_submission"]:
                in_scope_list.append(scope_info)
            else:
                out_of_scope_list.append(scope_info)

    return in_scope_list, out_of_scope_list

def hackerone_private(username, api_token):
    auth = (username, api_token)

    max_results = 200

    page_number = 0
    programs_list = []

    while True:
        response = requests.get(f"https://api.hackerone.com/v1/hackers/programs?page[size]=100&page[number]={page_number}", auth=auth)

        if response.status_code not in [200, 404]:
            print(f"Request returned {response.status_code}!")
            sys.exit()

        data = response.json()

        if response.status_code == 404 or len(data["data"]) == 0:
            break

        programs_list.extend(data["data"])
        page_number += 1

    # Reversing the list
    programs_list = programs_list[::-1]

    count = 0
    json_output = []
    for program in programs_list:
        if count == max_results:
            break

        program_handle = program["attributes"]["handle"]
        program_scope = get_program_scope(program_handle, username, api_token, False, False, False)
        if program_scope:
            scope_info = program_scope

            program_info = {
                    "Program": program["attributes"]["name"],
                    "Creation Date": program["attributes"]["started_accepting_at"],
                    "Program Type": "Public" if program["attributes"]["state"] == "public_mode" else "Private",
                    "Scope": scope_info
            }
            if program_info["Program Type"] != "Public":
                json_output.append(program_info)
        count +=1
    return json_output

def hackerone_last_three_months(username, api_token, private, reward, wildcard, mobile_app, url):
    auth = (username, api_token)

    max_results = 200

    page_number = 0
    programs_list = []

    while True:
        response = requests.get(f"https://api.hackerone.com/v1/hackers/programs?page[size]=100&page[number]={page_number}", auth=auth)

        if response.status_code not in [200, 404]:
            print(f"Request returned {response.status_code}!")
            sys.exit()

        data = response.json()

        if response.status_code == 404 or len(data["data"]) == 0:
            break

        programs_list.extend(data["data"])
        page_number += 1

    # Reversing the list
    programs_list = programs_list[::-1]

    count = 0
    json_output = []
    current_date = datetime.now(pytz.utc)
    three_months_ago = current_date - timedelta(days=90)

    for program in programs_list:
        if count == max_results:
            break

        program_handle = program["attributes"]["handle"]
        program_info = {
            "Program Name": program["attributes"]["name"],
            "Program Type": "Public" if program["attributes"]["state"] == "public_mode" else "Private",
            "Offer Rewards": ("True" if program["attributes"]["offers_bounties"] else "False"),
            "Creation Date": program["attributes"]["started_accepting_at"]
        }
        # Function to check if any scope item was updated in the last 90 days
        def is_updated_recently(scope_list):
            for item in scope_list:
                updated_str = item.get("Last Updated")
                if updated_str:
                    updated_date = dateutil.parser.parse(updated_str)
                    if not updated_date.tzinfo:
                        updated_date = updated_date.replace(tzinfo=pytz.utc)
                    if updated_date >= three_months_ago:
                        return True
            return False

        # Conditions for type of program == "private/soft_launched"
        if private:
            if program_info["Program Type"] == "Private":
                if wildcard:
                    if url and mobile_app:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for private program offering reward with all the scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    creation_date_str = program["attributes"]["started_accepting_at"]
                                    creation_date = dateutil.parser.parse(creation_date_str)

                                    if not creation_date.tzinfo:
                                        creation_date = creation_date.replace(tzinfo=pytz.utc)

                                    # Check if the program creation date, updated date, or any scope item was updated recently
                                    if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                        else:
                            # When user asking for private VDP program with all the scopes.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                creation_date_str = program["attributes"]["started_accepting_at"]
                                creation_date = dateutil.parser.parse(creation_date_str)

                                if not creation_date.tzinfo:
                                    creation_date = creation_date.replace(tzinfo=pytz.utc)

                                if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                    elif url:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for private program offering reward with wildcard and urls in scope.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    creation_date_str = program["attributes"]["started_accepting_at"]
                                    creation_date = dateutil.parser.parse(creation_date_str)

                                    if not creation_date.tzinfo:
                                        creation_date = creation_date.replace(tzinfo=pytz.utc)

                                    if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                        else:
                            # When user asking for private VDP program with wildcard and urls in scope.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                creation_date_str = program["attributes"]["started_accepting_at"]
                                creation_date = dateutil.parser.parse(creation_date_str)

                                if not creation_date.tzinfo:
                                    creation_date = creation_date.replace(tzinfo=pytz.utc)

                                if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                    elif mobile_app:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for private program offering reward with wildcard and mobile apps in scope.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    creation_date_str = program["attributes"]["started_accepting_at"]
                                    creation_date = dateutil.parser.parse(creation_date_str)

                                    if not creation_date.tzinfo:
                                        creation_date = creation_date.replace(tzinfo=pytz.utc)

                                    if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                        else:
                            # When user asking for private VDP program with wildcard and mobile apps in scope.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                creation_date_str = program["attributes"]["started_accepting_at"]
                                creation_date = dateutil.parser.parse(creation_date_str)

                                if not creation_date.tzinfo:
                                    creation_date = creation_date.replace(tzinfo=pytz.utc)

                                if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                    else:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for private program offering reward with only wildcard scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    creation_date_str = program["attributes"]["started_accepting_at"]
                                    creation_date = dateutil.parser.parse(creation_date_str)

                                    if not creation_date.tzinfo:
                                        creation_date = creation_date.replace(tzinfo=pytz.utc)

                                    if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                        else:
                            # When user asking for private VDP program with only wildcard scopes.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                creation_date_str = program["attributes"]["started_accepting_at"]
                                creation_date = dateutil.parser.parse(creation_date_str)

                                if not creation_date.tzinfo:
                                    creation_date = creation_date.replace(tzinfo=pytz.utc)

                                if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)

                # When the user selected for url and private with other filter conditions.
                elif url:
                    if wildcard and mobile_app:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for private program offering reward with all the scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    creation_date_str = program["attributes"]["started_accepting_at"]
                                    creation_date = dateutil.parser.parse(creation_date_str)

                                    if not creation_date.tzinfo:
                                        creation_date = creation_date.replace(tzinfo=pytz.utc)

                                    if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                        else:
                            # When user asking for private VDP program with all the scopes.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                creation_date_str = program["attributes"]["started_accepting_at"]
                                creation_date = dateutil.parser.parse(creation_date_str)

                                if not creation_date.tzinfo:
                                    creation_date = creation_date.replace(tzinfo=pytz.utc)

                                if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                    elif wildcard:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for private program offering reward with wildcard and urls in scope.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    creation_date_str = program["attributes"]["started_accepting_at"]
                                    creation_date = dateutil.parser.parse(creation_date_str)

                                    if not creation_date.tzinfo:
                                        creation_date = creation_date.replace(tzinfo=pytz.utc)

                                    if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                        else:
                            # When user asking for private VDP program with wildcard and urls in scope.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                creation_date_str = program["attributes"]["started_accepting_at"]
                                creation_date = dateutil.parser.parse(creation_date_str)

                                if not creation_date.tzinfo:
                                    creation_date = creation_date.replace(tzinfo=pytz.utc)

                                if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                    elif mobile_app:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for private program offering reward with urls and mobile apps in scope.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    creation_date_str = program["attributes"]["started_accepting_at"]
                                    creation_date = dateutil.parser.parse(creation_date_str)

                                    if not creation_date.tzinfo:
                                        creation_date = creation_date.replace(tzinfo=pytz.utc)

                                    if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                        else:
                            # When user asking for private VDP program with wildcard and mobile apps in scope.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                creation_date_str = program["attributes"]["started_accepting_at"]
                                creation_date = dateutil.parser.parse(creation_date_str)

                                if not creation_date.tzinfo:
                                    creation_date = creation_date.replace(tzinfo=pytz.utc)

                                if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                    else:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for private program offering reward with only urls scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    creation_date_str = program["attributes"]["started_accepting_at"]
                                    creation_date = dateutil.parser.parse(creation_date_str)

                                    if not creation_date.tzinfo:
                                        creation_date = creation_date.replace(tzinfo=pytz.utc)

                                    if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                        else:
                            # When user asking for private VDP program with only urls scopes.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                creation_date_str = program["attributes"]["started_accepting_at"]
                                creation_date = dateutil.parser.parse(creation_date_str)

                                if not creation_date.tzinfo:
                                    creation_date = creation_date.replace(tzinfo=pytz.utc)

                                if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)

                # When the user selected for mobile apps and private program with other filters.
                elif mobile_app:
                    if wildcard and mobile_app:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for private program offering reward with all the scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    creation_date_str = program["attributes"]["started_accepting_at"]
                                    creation_date = dateutil.parser.parse(creation_date_str)

                                    if not creation_date.tzinfo:
                                        creation_date = creation_date.replace(tzinfo=pytz.utc)

                                    if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                        else:
                            # When user asking for private VDP program with all the scopes.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                creation_date_str = program["attributes"]["started_accepting_at"]
                                creation_date = dateutil.parser.parse(creation_date_str)

                                if not creation_date.tzinfo:
                                    creation_date = creation_date.replace(tzinfo=pytz.utc)

                                if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                    elif url:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for private program offering reward with mobile apps and urls in scope.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    creation_date_str = program["attributes"]["started_accepting_at"]
                                    creation_date = dateutil.parser.parse(creation_date_str)

                                    if not creation_date.tzinfo:
                                        creation_date = creation_date.replace(tzinfo=pytz.utc)

                                    if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                        else:
                            # When user asking for private VDP program with wildcard and urls in scope.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                creation_date_str = program["attributes"]["started_accepting_at"]
                                creation_date = dateutil.parser.parse(creation_date_str)

                                if not creation_date.tzinfo:
                                    creation_date = creation_date.replace(tzinfo=pytz.utc)

                                if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                    elif wildcard:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for private program offering reward with wildcard and mobile apps in scope.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    creation_date_str = program["attributes"]["started_accepting_at"]
                                    creation_date = dateutil.parser.parse(creation_date_str)

                                    if not creation_date.tzinfo:
                                        creation_date = creation_date.replace(tzinfo=pytz.utc)

                                    if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                        else:
                            # When user asking for private VDP program with wildcard and mobile apps in scope.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                creation_date_str = program["attributes"]["started_accepting_at"]
                                creation_date = dateutil.parser.parse(creation_date_str)

                                if not creation_date.tzinfo:
                                    creation_date = creation_date.replace(tzinfo=pytz.utc)

                                if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                    else:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for private program offering reward with only mobile applications scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    creation_date_str = program["attributes"]["started_accepting_at"]
                                    creation_date = dateutil.parser.parse(creation_date_str)

                                    if not creation_date.tzinfo:
                                        creation_date = creation_date.replace(tzinfo=pytz.utc)

                                    if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                        else:
                            # When user asking for private VDP program with only mobile applications scopes.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                creation_date_str = program["attributes"]["started_accepting_at"]
                                creation_date = dateutil.parser.parse(creation_date_str)

                                if not creation_date.tzinfo:
                                    creation_date = creation_date.replace(tzinfo=pytz.utc)

                                if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)

                # When only private program required without any filters in the scope.
                else:
                    if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for private program offering reward with all scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    creation_date_str = program["attributes"]["started_accepting_at"]
                                    creation_date = dateutil.parser.parse(creation_date_str)

                                    if not creation_date.tzinfo:
                                        creation_date = creation_date.replace(tzinfo=pytz.utc)

                                    if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                    else:
                        # When user asking for private VDP program with all scopes.
                        program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                        if program_INscope or program_OUTscope:
                            creation_date_str = program["attributes"]["started_accepting_at"]
                            creation_date = dateutil.parser.parse(creation_date_str)

                            if not creation_date.tzinfo:
                                creation_date = creation_date.replace(tzinfo=pytz.utc)

                            if creation_date >= three_months_ago:
                                program_info["Program In-Scope Items"] = program_INscope
                                program_info["Program Out-Scope Items"] = program_OUTscope
                                json_output.append(program_info)

        # Condition for type of program == "public/public_mode --- When the above private condition is False."
        else:
            if program_info["Program Type"] == "Public":
                if wildcard:
                    if url and mobile_app:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for public program offering reward with all the scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    creation_date_str = program["attributes"]["started_accepting_at"]
                                    creation_date = dateutil.parser.parse(creation_date_str)

                                    if not creation_date.tzinfo:
                                        creation_date = creation_date.replace(tzinfo=pytz.utc)

                                    if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                        else:
                            # When user asking for public VDP program with all the scopes.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                creation_date_str = program["attributes"]["started_accepting_at"]
                                creation_date = dateutil.parser.parse(creation_date_str)

                                if not creation_date.tzinfo:
                                    creation_date = creation_date.replace(tzinfo=pytz.utc)

                                if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                    elif url:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for public program offering reward with wildcard and urls in scope.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    creation_date_str = program["attributes"]["started_accepting_at"]
                                    creation_date = dateutil.parser.parse(creation_date_str)

                                    if not creation_date.tzinfo:
                                        creation_date = creation_date.replace(tzinfo=pytz.utc)

                                    if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                        else:
                            # When user asking for public VDP program with wildcard and urls in scope.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                creation_date_str = program["attributes"]["started_accepting_at"]
                                creation_date = dateutil.parser.parse(creation_date_str)

                                if not creation_date.tzinfo:
                                    creation_date = creation_date.replace(tzinfo=pytz.utc)

                                if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                    elif mobile_app:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for public program offering reward with wildcard and mobile apps in scope.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    creation_date_str = program["attributes"]["started_accepting_at"]
                                    creation_date = dateutil.parser.parse(creation_date_str)

                                    if not creation_date.tzinfo:
                                        creation_date = creation_date.replace(tzinfo=pytz.utc)

                                    if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                        else:
                            # When user asking for public VDP program with wildcard and mobile apps in scope.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                creation_date_str = program["attributes"]["started_accepting_at"]
                                creation_date = dateutil.parser.parse(creation_date_str)

                                if not creation_date.tzinfo:
                                    creation_date = creation_date.replace(tzinfo=pytz.utc)

                                if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                    else:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for public program offering reward with only wildcard scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    creation_date_str = program["attributes"]["started_accepting_at"]
                                    creation_date = dateutil.parser.parse(creation_date_str)

                                    if not creation_date.tzinfo:
                                        creation_date = creation_date.replace(tzinfo=pytz.utc)

                                    if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                        else:
                            # When user asking for public VDP program with only wildcard scopes.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                creation_date_str = program["attributes"]["started_accepting_at"]
                                creation_date = dateutil.parser.parse(creation_date_str)

                                if not creation_date.tzinfo:
                                    creation_date = creation_date.replace(tzinfo=pytz.utc)

                                if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)

                # When the user selected for url and public with other filter conditions.
                elif url:
                    if wildcard and mobile_app:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for public program offering reward with all the scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    creation_date_str = program["attributes"]["started_accepting_at"]
                                    creation_date = dateutil.parser.parse(creation_date_str)

                                    if not creation_date.tzinfo:
                                        creation_date = creation_date.replace(tzinfo=pytz.utc)

                                    if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                        else:
                            # When user asking for public VDP program with all the scopes.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                creation_date_str = program["attributes"]["started_accepting_at"]
                                creation_date = dateutil.parser.parse(creation_date_str)

                                if not creation_date.tzinfo:
                                    creation_date = creation_date.replace(tzinfo=pytz.utc)

                                if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                    elif wildcard:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for public program offering reward with wildcard and urls in scope.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    creation_date_str = program["attributes"]["started_accepting_at"]
                                    creation_date = dateutil.parser.parse(creation_date_str)

                                    if not creation_date.tzinfo:
                                        creation_date = creation_date.replace(tzinfo=pytz.utc)

                                    if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                        else:
                            # When user asking for public VDP program with wildcard and urls in scope.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                creation_date_str = program["attributes"]["started_accepting_at"]
                                creation_date = dateutil.parser.parse(creation_date_str)

                                if not creation_date.tzinfo:
                                    creation_date = creation_date.replace(tzinfo=pytz.utc)

                                if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                    elif mobile_app:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for public program offering reward with urls and mobile apps in scope.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    creation_date_str = program["attributes"]["started_accepting_at"]
                                    creation_date = dateutil.parser.parse(creation_date_str)

                                    if not creation_date.tzinfo:
                                        creation_date = creation_date.replace(tzinfo=pytz.utc)

                                    if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                        else:
                            # When user asking for public VDP program with wildcard and mobile apps in scope.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                creation_date_str = program["attributes"]["started_accepting_at"]
                                creation_date = dateutil.parser.parse(creation_date_str)

                                if not creation_date.tzinfo:
                                    creation_date = creation_date.replace(tzinfo=pytz.utc)

                                if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                    else:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for public program offering reward with only urls scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    creation_date_str = program["attributes"]["started_accepting_at"]
                                    creation_date = dateutil.parser.parse(creation_date_str)

                                    if not creation_date.tzinfo:
                                        creation_date = creation_date.replace(tzinfo=pytz.utc)

                                    if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                        else:
                            # When user asking for public VDP program with only urls scopes.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                creation_date_str = program["attributes"]["started_accepting_at"]
                                creation_date = dateutil.parser.parse(creation_date_str)

                                if not creation_date.tzinfo:
                                    creation_date = creation_date.replace(tzinfo=pytz.utc)

                                if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)

                # When the user selected for mobile apps and public program with other filters.
                elif mobile_app:
                    if wildcard and mobile_app:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for public program offering reward with all the scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    creation_date_str = program["attributes"]["started_accepting_at"]
                                    creation_date = dateutil.parser.parse(creation_date_str)

                                    if not creation_date.tzinfo:
                                        creation_date = creation_date.replace(tzinfo=pytz.utc)

                                    if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                        else:
                            # When user asking for public VDP program with all the scopes.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                creation_date_str = program["attributes"]["started_accepting_at"]
                                creation_date = dateutil.parser.parse(creation_date_str)

                                if not creation_date.tzinfo:
                                    creation_date = creation_date.replace(tzinfo=pytz.utc)

                                if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                    elif url:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for public program offering reward with mobile apps and urls in scope.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    creation_date_str = program["attributes"]["started_accepting_at"]
                                    creation_date = dateutil.parser.parse(creation_date_str)

                                    if not creation_date.tzinfo:
                                        creation_date = creation_date.replace(tzinfo=pytz.utc)

                                    if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                        else:
                            # When user asking for public VDP program with wildcard and urls in scope.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                creation_date_str = program["attributes"]["started_accepting_at"]
                                creation_date = dateutil.parser.parse(creation_date_str)

                                if not creation_date.tzinfo:
                                    creation_date = creation_date.replace(tzinfo=pytz.utc)

                                if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                    elif wildcard:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for public program offering reward with wildcard and mobile apps in scope.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    creation_date_str = program["attributes"]["started_accepting_at"]
                                    creation_date = dateutil.parser.parse(creation_date_str)

                                    if not creation_date.tzinfo:
                                        creation_date = creation_date.replace(tzinfo=pytz.utc)

                                    if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                        else:
                            # When user asking for public VDP program with wildcard and mobile apps in scope.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                creation_date_str = program["attributes"]["started_accepting_at"]
                                creation_date = dateutil.parser.parse(creation_date_str)

                                if not creation_date.tzinfo:
                                    creation_date = creation_date.replace(tzinfo=pytz.utc)

                                if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                    else:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for public program offering reward with only mobile applications scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    creation_date_str = program["attributes"]["started_accepting_at"]
                                    creation_date = dateutil.parser.parse(creation_date_str)

                                    if not creation_date.tzinfo:
                                        creation_date = creation_date.replace(tzinfo=pytz.utc)

                                    if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                        program_info["Program In-Scope Items"] = program_INscope
                                        program_info["Program Out-Scope Items"] = program_OUTscope
                                        json_output.append(program_info)
                        else:
                            # When user asking for public VDP program with only mobile applications scopes.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                creation_date_str = program["attributes"]["started_accepting_at"]
                                creation_date = dateutil.parser.parse(creation_date_str)

                                if not creation_date.tzinfo:
                                    creation_date = creation_date.replace(tzinfo=pytz.utc)

                                if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)

            # When only public program required without any filters in the scope.
            else:
                if reward:
                        if program_info["Offer Rewards"] == "True":
                            # When user asking for public program offering reward with all scopes.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                creation_date_str = program["attributes"]["started_accepting_at"]
                                creation_date = dateutil.parser.parse(creation_date_str)

                                if not creation_date.tzinfo:
                                    creation_date = creation_date.replace(tzinfo=pytz.utc)

                                if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)

                else:
                    # When user asking for public VDP program with all scopes.
                    program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                    if program_INscope or program_OUTscope:
                        creation_date_str = program["attributes"]["started_accepting_at"]
                        creation_date = dateutil.parser.parse(creation_date_str)

                        if not creation_date.tzinfo:
                            creation_date = creation_date.replace(tzinfo=pytz.utc)

                        if ((creation_date and creation_date >= three_months_ago) or (program_INscope and is_updated_recently(program_INscope)) or (program_OUTscope and is_updated_recently(program_OUTscope))):
                            program_info["Program In-Scope Items"] = program_INscope
                            program_info["Program Out-Scope Items"] = program_OUTscope
                            json_output.append(program_info)
        count +=1

    return json_output

def get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app):
    auth = (username, api_token)

    # Constructing the API request URL
    request_url = f"https://api.hackerone.com/v1/hackers/programs/{program_handle}/structured_scopes?page%5Bsize%5D=100"

    # Making the GET request to the HackerOne API for fetching the program scope with the page size to max=100.
    r = requests.get(request_url, auth=auth)
    if r.status_code != 200:
        print(f"Request returned {r.status_code}!")
        sys.exit()

    data = r.json()

    in_scope_list = []
    out_of_scope_list = []
    for scope in data["data"]:
        # Filtering based on provided parameters (wildcard, url, mobile_app)
        asset_type = scope["attributes"]["asset_type"]

        # For WILDCARD Scope
        if (wildcard and asset_type == "WILDCARD"):
            scope_info = {
                "Asset": scope["attributes"]["asset_identifier"],
                "Type": asset_type,
                "Last Updated": scope["attributes"]["updated_at"],
                "State": "In-Scope" if scope["attributes"]["eligible_for_submission"] else "Out-of-Scope",
                "Eligible for Bounty": "Yes" if scope["attributes"].get("eligible_for_bounty", False) else "No",
                # "Instruction": scope["attributes"].get("instruction", "None"),
                "Max Severity": scope["attributes"].get("max_severity", "None")
            }

            # Adding scope to the appropriate list
            if scope["attributes"]["eligible_for_submission"]:
                in_scope_list.append(scope_info)
            else:
                out_of_scope_list.append(scope_info)

        # For URL Scope
        if (url and asset_type == "URL"):
            scope_info = {
                "Asset": scope["attributes"]["asset_identifier"],
                "Last Updated": scope["attributes"]["updated_at"],
                "Type": asset_type,
                "State": "In-Scope" if scope["attributes"]["eligible_for_submission"] else "Out-of-Scope",
                "Eligible for Bounty": "Yes" if scope["attributes"].get("eligible_for_bounty", False) else "No",
                # "Instruction": scope["attributes"].get("instruction", "None"),
                "Max Severity": scope["attributes"].get("max_severity", "None")
            }

            # Adding scope to the appropriate list
            if scope["attributes"]["eligible_for_submission"]:
                in_scope_list.append(scope_info)
            else:
                out_of_scope_list.append(scope_info)

        # For Mobile Applications Scope
        if (mobile_app and asset_type == "APPLE_STORE_APP_ID") or (mobile_app and asset_type == "GOOGLE_PLAY_APP_ID"):
            scope_info = {
                "Asset": scope["attributes"]["asset_identifier"],
                "Last Updated": scope["attributes"]["updated_at"],
                "Type": asset_type,
                "State": "In-Scope" if scope["attributes"]["eligible_for_submission"] else "Out-of-Scope",
                "Eligible for Bounty": "Yes" if scope["attributes"].get("eligible_for_bounty", False) else "No",
                # "Instruction": scope["attributes"].get("instruction", "None"),
                "Max Severity": scope["attributes"].get("max_severity", "None")
            }

            # Adding scope to the appropriate list
            if scope["attributes"]["eligible_for_submission"]:
                in_scope_list.append(scope_info)
            else:
                out_of_scope_list.append(scope_info)

        # For all the scopes
        if not wildcard and not url and not mobile_app:
            scope_info = {
                "Asset": scope["attributes"]["asset_identifier"],
                "Type": asset_type,
                "Last Updated": scope["attributes"]["updated_at"],
                "State": "In-Scope" if scope["attributes"]["eligible_for_submission"] else "Out-of-Scope",
                "Eligible for Bounty": "Yes" if scope["attributes"].get("eligible_for_bounty", False) else "No",
                "Max Severity": scope["attributes"].get("max_severity", "None")
            }

            # Adding scope to the appropriate list
            if scope["attributes"]["eligible_for_submission"]:
                in_scope_list.append(scope_info)
            else:
                out_of_scope_list.append(scope_info)

    return in_scope_list, out_of_scope_list

def get_h1_programs(username, api_token, private, reward, wildcard, mobile_app, url):

    max_results = 600
    auth = (username, api_token)
    programs_list = []
    page_number = 0

    while len(programs_list) < max_results:
        pages_to_fetch = min(10, (max_results - len(programs_list)) // 100)

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_page = {executor.submit(fetch_programs_page, page, auth): page for page in range(page_number, page_number + pages_to_fetch)}

            for future in as_completed(future_to_page):
                data = future.result()
                if data:
                    programs_list.extend(data)
                    if len(programs_list) >= max_results:
                        # Trim the list to the max_results if overfilled
                        programs_list = programs_list[:max_results]
                        break

            page_number += pages_to_fetch


    # Reversing the list
    programs_list = programs_list[::-1]

    count = 0
    json_output = []
    for program in programs_list:
        if count == max_results:
            break

        program_handle = program["attributes"]["handle"]
        program_info = {
            "Program Name": program["attributes"]["name"],
            "Program Handle": program_handle,
            "Program Type": "Public" if program["attributes"]["state"] == "public_mode" else "Private",
            "Offer Rewards": ("True" if program["attributes"]["offers_bounties"] else "False"),
            "Creation date": program["attributes"]["started_accepting_at"],
        }

        # Conditions for type of program == "private/soft_launched"
        if private:
            if program["attributes"]["state"] == "soft_launched":
                if wildcard:
                    if url and mobile_app:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for private program offering reward with all the scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                        else:
                            # When user asking for private VDP program with all the scopes.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                program_info["Program In-Scope Items"] = program_INscope
                                program_info["Program Out-Scope Items"] = program_OUTscope
                                json_output.append(program_info)
                    elif url:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for private program offering reward with wildcard and urls in scope.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                        else:
                            # When user asking for private VDP program with wildcard and urls in scope.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                program_info["Program In-Scope Items"] = program_INscope
                                program_info["Program Out-Scope Items"] = program_OUTscope
                                json_output.append(program_info)
                    elif mobile_app:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for private program offering reward with wildcard and mobile apps in scope.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                        else:
                            # When user asking for private VDP program with wildcard and mobile apps in scope.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                program_info["Program In-Scope Items"] = program_INscope
                                program_info["Program Out-Scope Items"] = program_OUTscope
                                json_output.append(program_info)
                    else:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for private program offering reward with only wildcard scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                        else:
                            # When user asking for private VDP program with only wildcard scopes.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope:
                                program_info["Program In-Scope Items"] = program_INscope
                                # program_info["Program Out-Scope Items"] = program_OUTscope
                                json_output.append(program_info)

                # When the user selected for url and private with other filter conditions.
                elif url:
                    if wildcard and mobile_app:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for private program offering reward with all the scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                        else:
                            # When user asking for private VDP program with all the scopes.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                program_info["Program In-Scope Items"] = program_INscope
                                program_info["Program Out-Scope Items"] = program_OUTscope
                                json_output.append(program_info)
                    elif wildcard:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for private program offering reward with wildcard and urls in scope.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                        else:
                            # When user asking for private VDP program with wildcard and urls in scope.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                program_info["Program In-Scope Items"] = program_INscope
                                program_info["Program Out-Scope Items"] = program_OUTscope
                                json_output.append(program_info)
                    elif mobile_app:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for private program offering reward with urls and mobile apps in scope.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                        else:
                            # When user asking for private VDP program with wildcard and mobile apps in scope.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                program_info["Program In-Scope Items"] = program_INscope
                                program_info["Program Out-Scope Items"] = program_OUTscope
                                json_output.append(program_info)
                    else:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for private program offering reward with only urls scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                        else:
                            # When user asking for private VDP program with only urls scopes.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                program_info["Program In-Scope Items"] = program_INscope
                                program_info["Program Out-Scope Items"] = program_OUTscope
                                json_output.append(program_info)

                # When the user selected for mobile apps and private program with other filters.
                elif mobile_app:
                    if wildcard and mobile_app:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for private program offering reward with all the scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                        else:
                            # When user asking for private VDP program with all the scopes.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                program_info["Program In-Scope Items"] = program_INscope
                                program_info["Program Out-Scope Items"] = program_OUTscope
                                json_output.append(program_info)
                    elif url:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for private program offering reward with mobile apps and urls in scope.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                        else:
                            # When user asking for private VDP program with wildcard and urls in scope.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                program_info["Program In-Scope Items"] = program_INscope
                                program_info["Program Out-Scope Items"] = program_OUTscope
                                json_output.append(program_info)
                    elif wildcard:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for private program offering reward with wildcard and mobile apps in scope.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                        else:
                            # When user asking for private VDP program with wildcard and mobile apps in scope.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                program_info["Program In-Scope Items"] = program_INscope
                                program_info["Program Out-Scope Items"] = program_OUTscope
                                json_output.append(program_info)
                    else:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for private program offering reward with only mobile applications scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                        else:
                            # When user asking for private VDP program with only mobile applications scopes.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                program_info["Program In-Scope Items"] = program_INscope
                                program_info["Program Out-Scope Items"] = program_OUTscope
                                json_output.append(program_info)

                # When only private program required without any filters in the scope.
                else:
                    if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for private program offering reward with all scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                    else:
                        # When user asking for private VDP program with all scopes.
                        program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                        if program_INscope or program_OUTscope:
                            program_info["Program In-Scope Items"] = program_INscope
                            program_info["Program Out-Scope Items"] = program_OUTscope
                            json_output.append(program_info)

        # Condition for type of program == "public/public_mode --- When the above private condition is False."
        else:
            if program_info["Program Type"] == "Public":
                if wildcard:
                    if url and mobile_app:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for public program offering reward with all the scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                        else:
                            # When user asking for public VDP program with all the scopes.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                program_info["Program In-Scope Items"] = program_INscope
                                program_info["Program Out-Scope Items"] = program_OUTscope
                                json_output.append(program_info)
                    elif url:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for public program offering reward with wildcard and urls in scope.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                        else:
                            # When user asking for public VDP program with wildcard and urls in scope.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                program_info["Program In-Scope Items"] = program_INscope
                                program_info["Program Out-Scope Items"] = program_OUTscope
                                json_output.append(program_info)
                    elif mobile_app:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for public program offering reward with wildcard and mobile apps in scope.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                        else:
                            # When user asking for public VDP program with wildcard and mobile apps in scope.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                program_info["Program In-Scope Items"] = program_INscope
                                program_info["Program Out-Scope Items"] = program_OUTscope
                                json_output.append(program_info)
                    else:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for public program offering reward with only wildcard scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                        else:
                            # When user asking for public VDP program with only wildcard scopes.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                program_info["Program In-Scope Items"] = program_INscope
                                program_info["Program Out-Scope Items"] = program_OUTscope
                                json_output.append(program_info)

                # When the user selected for url and public with other filter conditions.
                elif url:
                    if wildcard and mobile_app:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for public program offering reward with all the scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                        else:
                            # When user asking for public VDP program with all the scopes.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                program_info["Program In-Scope Items"] = program_INscope
                                program_info["Program Out-Scope Items"] = program_OUTscope
                                json_output.append(program_info)
                    elif wildcard:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for public program offering reward with wildcard and urls in scope.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                        else:
                            # When user asking for public VDP program with wildcard and urls in scope.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                program_info["Program In-Scope Items"] = program_INscope
                                program_info["Program Out-Scope Items"] = program_OUTscope
                                json_output.append(program_info)
                    elif mobile_app:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for public program offering reward with urls and mobile apps in scope.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                        else:
                            # When user asking for public VDP program with wildcard and mobile apps in scope.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                program_info["Program In-Scope Items"] = program_INscope
                                program_info["Program Out-Scope Items"] = program_OUTscope
                                json_output.append(program_info)
                    else:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for public program offering reward with only urls scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                        else:
                            # When user asking for public VDP program with only urls scopes.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                program_info["Program In-Scope Items"] = program_INscope
                                program_info["Program Out-Scope Items"] = program_OUTscope
                                json_output.append(program_info)

                # When the user selected for mobile apps and public program with other filters.
                elif mobile_app:
                    if wildcard and mobile_app:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for public program offering reward with all the scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                        else:
                            # When user asking for public VDP program with all the scopes.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                program_info["Program In-Scope Items"] = program_INscope
                                program_info["Program Out-Scope Items"] = program_OUTscope
                                json_output.append(program_info)
                    elif url:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for public program offering reward with mobile apps and urls in scope.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                        else:
                            # When user asking for public VDP program with wildcard and urls in scope.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                program_info["Program In-Scope Items"] = program_INscope
                                program_info["Program Out-Scope Items"] = program_OUTscope
                                json_output.append(program_info)
                    elif wildcard:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for public program offering reward with wildcard and mobile apps in scope.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                        else:
                            # When user asking for public VDP program with wildcard and mobile apps in scope.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                program_info["Program In-Scope Items"] = program_INscope
                                program_info["Program Out-Scope Items"] = program_OUTscope
                                json_output.append(program_info)
                    else:
                        if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for public program offering reward with only mobile applications scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                        else:
                            # When user asking for public VDP program with only mobile applications scopes.
                            program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                            if program_INscope or program_OUTscope:
                                program_info["Program In-Scope Items"] = program_INscope
                                program_info["Program Out-Scope Items"] = program_OUTscope
                                json_output.append(program_info)

                # When only public program required without any filters in the scope.
                else:
                    if reward:
                            if program_info["Offer Rewards"] == "True":
                                # When user asking for public program offering reward with all scopes.
                                program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                                if program_INscope or program_OUTscope:
                                    program_info["Program In-Scope Items"] = program_INscope
                                    program_info["Program Out-Scope Items"] = program_OUTscope
                                    json_output.append(program_info)
                    else:
                        # When user asking for public VDP program with all scopes.
                        program_INscope, program_OUTscope = get_program_scope(program_handle, username, api_token, wildcard, url, mobile_app)
                        if program_INscope or program_OUTscope:
                            program_info["Program In-Scope Items"] = program_INscope
                            program_info["Program Out-Scope Items"] = program_OUTscope
                            json_output.append(program_info)

        count += 1

    return json_output
