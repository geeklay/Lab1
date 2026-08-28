import json
import requests
import csv
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

if not os.path.exists("data"):
 os.makedirs("data")

# GitHub Authentication function
def github_auth(url, token):
    jsonData = None
    try:
        headers = {'Authorization': 'Bearer {}'.format(token)}
        request = requests.get(url, headers=headers)
        jsonData = json.loads(request.content)
    except Exception as e:
        pass
        print(e)
    return jsonData

def is_source(filename):
    SOURCE_EXTENSIONS = [
        ".java",
        ".kt",
        ".cpp",
        ".h"
    ]
    return any(filename.endswith(ext) for ext in SOURCE_EXTENSIONS)

# @dictFiles, empty dictionary of files
# @token, GitHub authentication token
# @repo, GitHub repo
# @branch, GitHub branch
def countfiles(dictfiles, token, repo, branch):
    ipage = 1  # url page counter

    try:
        # loop though all the commit pages until the last returned empty page
        while True:
            spage = str(ipage)
            commitsUrl = 'https://api.github.com/repos/' + repo + '/commits?sha=' + branch + '&page=' + spage + '&per_page=100'
            jsonCommits = github_auth(commitsUrl, token)

            # break out of the while loop if there are no more commits in the pages
            if len(jsonCommits) == 0:
                break
            # iterate through the list of commits in  spage
            for shaObject in jsonCommits:
                sha = shaObject['sha']
                # For each commit, use the GitHub commit API to extract the files touched by the commit
                shaUrl = 'https://api.github.com/repos/' + repo + '/commits/' + sha
                shaDetails = github_auth(shaUrl, token)
                filesjson = shaDetails['files']
                for filenameObj in filesjson:
                    filename = filenameObj['filename']

                    if is_source(filename):
                        dictfiles[filename] = dictfiles.get(filename, 0) + 1
                        print("adding " + filename)
                    else:
                        print("skipping " + filename + ' - not a source file')
            ipage += 1
    except:
        print("Error receiving data")
        exit(0)
# GitHub repo
repo = 'scottyab/rootbeer'
# repo = 'Skyscanner/backpack' # This repo is commit heavy. It takes long to finish executing
# repo = 'k9mail/k-9' # This repo is commit heavy. It takes long to finish executing
# repo = 'mendhak/gpslogger'

token = os.getenv("MIKEPODO_GH_TOKEN")
if not token:
    raise SystemExit("Set MIKEPODO_GH_TOKEN in repo_mining/.env")

branch = 'master'

dictfiles = dict()
countfiles(dictfiles, token, repo, branch)
print('Total number of files: ' + str(len(dictfiles)))

file = repo.split('/')[1]
# change this to the path of your file
fileOutput = 'data/mikepodo_file_' + file + '.csv'
rows = ["Filename", "Touches"]
fileCSV = open(fileOutput, 'w')
writer = csv.writer(fileCSV)
writer.writerow(rows)

bigcount = None
bigfilename = None
for filename, count in dictfiles.items():
    rows = [filename, count]
    writer.writerow(rows)
    if bigcount is None or count > bigcount:
        bigcount = count
        bigfilename = filename
fileCSV.close()
print('The file ' + bigfilename + ' has been touched ' + str(bigcount) + ' times.')
