import csv
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

repo = "scottyab/rootbeer"
branch = "master"

token = os.getenv("MIKEPODO_GH_TOKEN")
if not token:
    raise SystemExit("Set MIKEPODO_GH_TOKEN in repo_mining/.env")

repo_name = repo.split("/")[1]
csv_path = f"data/mikepodo_file_{repo_name}.csv"
json_path = f"data/mikepodo_authors_{repo_name}.json"


def github_get(url):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def commits_for_path(filepath):
    commits = []
    page = 1
    while True:
        url = (
            f"https://api.github.com/repos/{repo}/commits"
            f"?sha={branch}&path={filepath}&page={page}&per_page=100"
        )
        page_data = github_get(url)
        if not page_data:
            break
        for item in page_data:
            author_info = item.get("commit", {}).get("author", {})
            commits.append(
                {
                    "author": author_info.get("name"),
                    "date": author_info.get("date"),
                }
            )
        page += 1
    return commits


def load_file_paths(path):
    paths = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            filename = row.get("Filename")
            if filename:
                paths.append(filename)
    return paths

files = load_file_paths(csv_path)
results = []

for filepath in files:
    print(f"collecting commits for {filepath}")
    commits = commits_for_path(filepath)
    results.append(
        {
            "path": filepath,
            "changes": len(commits),
            "commits": commits,
        }
    )

with open(json_path, "w") as f:
    json.dump(results, f, indent=2)

print(f"Wrote {len(results)} files to {json_path}")

