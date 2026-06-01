# This script is executed when a new issue is created on our github repository. 
# In case the issue text consists only of a single line starting like a zenodo link, 
# it will retrieve all important details from the zenodo record, add it to a yml file
# and send a pull-request
import math
import math
import sys
from urllib import response
from _github_utilities import create_branch, get_file_in_repository, get_issue_body, write_file, send_pull_request
import yaml
import os
import requests
import shutil
import pandas as pd
from generate_link_lists import load_dataframe, update_yaml_file, complete_zenodo_data
from datetime import datetime

def main():
    """
    Main function to handle the process of retrieving Zenodo data and appending
    it to a YAML file in a GitHub repository.

    This function takes command-line arguments for the repository name and issue number,
    retrieves the issue body, checks if it's a valid Zenodo link, retrieves corresponding
    data, and appends it to a specified YAML file by creating a new branch and submitting
    a pull request.

    Returns
    -------
    None
    """
    repository = sys.argv[1]

    token = os.getenv('ZENODO_API_KEY')
    communities = ['nfdi4biodiv']

    yml_filename = "resources/nfdi4biodiversity.yml"

    # read "database"
    branch = create_branch(repository)
    print("New branch:", branch)
    log = []
    new_data = []

    # old data
    df = load_dataframe("resources/")
    all_urls = str(df["url"].tolist())

    for community in communities:
        log.append(f"# {community}")
        log.append(f"https://zenodo.org/communities/{community}")
        
        page_size = 10
        all_records = []
    
        # First page
        response = requests.get(
            "https://zenodo.org/api/records",
            params={
                "communities": community,
                "access_token": token,
                "page": 1,
                "size": page_size,
            },
        )
        response.raise_for_status()

        data = response.json()
        all_records.extend(data["hits"]["hits"])

        total = data["hits"]["total"]
        num_pages = math.ceil(total / page_size)
        num_pages

        # Remaining pages
        for page in range(2, num_pages + 1):
            print("Reading page ", page)
            response = requests.get(
                "https://zenodo.org/api/records",
                params={
                    "communities": community,
                    "access_token": token,
                    "page": page,
                    "size": page_size,
                },
            )
            response.raise_for_status()
            
            all_records.extend(response.json()["hits"]["hits"])

        print(f"Collected {len(all_records)} records")

        for record in all_records:
            data = zenodo_to_yml(record)
            url = record["links"]["self_html"]

            if isinstance(data["url"], str):
                data["url"] = [data["url"]]

            not_in_data_yet = True
            for u in data["url"]:
                if u in all_urls:
                    not_in_data_yet = False

            if not_in_data_yet:
                data['submission_date'] = datetime.now().isoformat()
                if "name" not in data:
                    data["name"] = "-"
                name = data["name"]
                log.append(f"* [{name}]({url})")
                new_data.append(data)

                # deal with entries listed in multiple communities
                all_urls = all_urls + "\n" + "\n".join([u for u in data["url"]])
        
            

    import yaml
    zenodo_yml = yaml.dump(new_data, allow_unicode=True) #.replace("\n", "\n  ")
    

    # save data in repository
    file_content = get_file_in_repository(repository, branch, yml_filename).decoded_content.decode()
    print("yml file content length:", len(file_content))

    # add entry
    file_content += zenodo_yml
    #print("zenodo_yml", len(zenodo_yml))

    # save back to github
    write_file(repository, branch, yml_filename, file_content, "Add entries from " + ", ".join(communities))

    log = "\n".join(log)
    res = send_pull_request(repository, branch, "Add content from communities: " + ", ".join(communities), f"Added contents:\n{log}")

    print("Done.", res)


def remove_html_tags(text):
    """
    Clean HTML code and turn it into plain text.
    """
    import re
    cleaned_text = re.sub('<.*?>', '', text)
    return cleaned_text

def zenodo_to_yml(zenodo_data):
    zenodo_url = zenodo_data["links"]["self_html"]
    
    entry = {}
    urls = [zenodo_url]

    if 'doi_url' in zenodo_data.keys():
        doi_url = zenodo_data['doi_url']

        # Add DOI URL to the URLs list if it's not already there
        if doi_url not in urls:
            urls.append(doi_url)
    entry['url'] = urls

    if 'metadata' in zenodo_data.keys():
        metadata = zenodo_data['metadata']
        # Update entry with Zenodo metadata and statistics
        entry['name'] = metadata['title']
        if 'publication_date' in metadata.keys():
            entry['publication_date'] = metadata['publication_date']
        if 'description' in metadata.keys():
            entry['description'] = remove_html_tags(metadata['description'])
        if 'creators' in metadata.keys():
            creators = metadata['creators']
            entry['authors'] = [c['name'] for c in creators]
        if 'license' in metadata.keys():
            entry['license'] = metadata['license']['id']

    if 'stats' in zenodo_data.keys():
        entry['num_downloads'] = zenodo_data['stats']['downloads']

    return entry



if __name__ == "__main__":
    main()
