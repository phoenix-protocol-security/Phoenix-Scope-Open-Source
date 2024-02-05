import requests
import concurrent.futures
import json


def get_total_pages(base_url):
    response = requests.get(base_url)
    if response.status_code == 200:
        data = response.json()
        return data['meta']['totalPages']
    else:
        print("Failed to fetch initial data")
        return 0

def fetch_program_urls_for_page(base_url, page):
    response = requests.get(f"{base_url}?page[]={page}")
    if response.status_code == 200:
        data = response.json()
        return [program.get("program_url", "") for program in data.get("programs", []) if program.get("program_url", "")]
    else:
        print(f"Failed to fetch data for page {page}")
        return []

def fetch_program_target_url(program_url):
    full_url = f"https://bugcrowd.com{program_url}/target_groups"
    response = requests.get(full_url)
    if response.status_code == 200:
        data = response.json()
        target_urls = [f"https://bugcrowd.com{group['targets_url']}" for group in data.get("groups", []) if group.get("targets_url", "")]
        return target_urls
    else:
        return []

def fetch_all_programs_and_targets_concurrently(base_url, total_pages):
    program_targets_dict = {}
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # First, fetch all program URLs
        page_futures = [executor.submit(fetch_program_urls_for_page, base_url, page) for page in range(1, total_pages + 1)]
        program_urls = []
        for future in concurrent.futures.as_completed(page_futures):
            program_urls.extend(future.result())

        # Next, fetch target URLs for each program
        target_futures = {executor.submit(fetch_program_target_url, url): url for url in program_urls}
        for future in concurrent.futures.as_completed(target_futures):
            program_url = f"https://bugcrowd.com{target_futures[future]}"
            target_urls = future.result()
            program_targets_dict[program_url] = target_urls

    return program_targets_dict

base_url = "https://bugcrowd.com/programs.json"
total_pages = get_total_pages(base_url)

if total_pages > 0:
    program_targets_dict = fetch_all_programs_and_targets_concurrently(base_url, total_pages)
    print(json.dumps(program_targets_dict, indent=2))
else:
    print("Could not retrieve total pages.")
