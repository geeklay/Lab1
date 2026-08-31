"""
Collect author and file-touch history for selected Rootbeer source files.

Assignment scope
----------------
For every source file selected using the same criteria as Task 1, this script
records:

- File path
- Authors who changed the file
- Dates of those changes
- Total number of times the file was changed
- Number of touches attributed to each author

The resulting JSON provides the detailed event data needed by the scatter-plot
script and executive summary.
"""

import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests


REPOSITORY = "scottyab/rootbeer"
SOURCE_EXTENSIONS = {".java", ".kt", ".cpp", ".c", ".h"}

SCRIPT_DIRECTORY = Path(__file__).resolve().parent
DATA_DIRECTORY = SCRIPT_DIRECTORY / "data"
OUTPUT_FILE = DATA_DIRECTORY / "kenner1-unlv_authors_rootbeer.json"

API_BASE_URL = "https://api.github.com"


def create_headers():
    """
    Create API headers using a token supplied at runtime.

    Reading GITHUB_TOKEN from the environment prevents credentials from being
    stored in source code or commit history.
    """
    github_token = os.getenv("GITHUB_TOKEN")

    if not github_token:
        raise RuntimeError(
            "GITHUB_TOKEN is not set. Export it before running this script."
        )

    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {github_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def github_get(url, params=None):
    """Request JSON from GitHub and report HTTP failures clearly."""
    response = requests.get(
        url,
        headers=create_headers(),
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_default_branch(repository):
    """Discover the default branch instead of assuming main or master."""
    repository_data = github_get(
        f"{API_BASE_URL}/repos/{repository}"
    )
    return repository_data["default_branch"]


def is_source_file(file_path):
    """Apply the same documented source definition used in Task 1."""
    return Path(file_path).suffix.lower() in SOURCE_EXTENSIONS


def collect_source_files(repository, branch):
    """Return current source files from the repository's default branch."""
    tree_data = github_get(
        f"{API_BASE_URL}/repos/{repository}/git/trees/{branch}",
        params={"recursive": "1"},
    )

    if tree_data.get("truncated"):
        raise RuntimeError(
            "GitHub returned a truncated repository tree."
        )

    source_files = sorted(
        item["path"]
        for item in tree_data["tree"]
        if item["type"] == "blob" and is_source_file(item["path"])
    )

    if not source_files:
        raise RuntimeError("No source files matched the selection criteria.")

    return source_files


def identify_author(commit_details):
    """
    Select a stable author label for the visualization.

    A linked GitHub username is preferred because it distinguishes accounts
    more reliably. If GitHub cannot associate the commit with an account, the
    author name stored inside the Git commit is used as a fallback.
    """
    github_author = commit_details.get("author")

    if github_author and github_author.get("login"):
        return github_author["login"]

    commit_author = commit_details.get("commit", {}).get("author", {})
    return commit_author.get("name") or "Unknown author"


def collect_file_history(repository, branch, source_files):
    """
    Collect dated author events for every selected source file.

    One touch represents one commit in which an author changed a selected file.
    Commit pages are processed until GitHub returns an empty page.
    """
    source_file_set = set(source_files)
    file_changes = {file_path: [] for file_path in source_files}
    repository_commit_dates = []
    page = 1

    while True:
        commits = github_get(
            f"{API_BASE_URL}/repos/{repository}/commits",
            params={
                "sha": branch,
                "page": page,
                "per_page": 100,
            },
        )

        if not commits:
            break

        print(f"Processing commit page {page}...")

        for commit_summary in commits:
            commit_details = github_get(
                f"{API_BASE_URL}/repos/{repository}/commits/"
                f"{commit_summary['sha']}"
            )

            author = identify_author(commit_details)
            change_date = commit_details["commit"]["author"]["date"]
            repository_commit_dates.append(change_date)

            for changed_file in commit_details.get("files", []):
                file_path = changed_file["filename"]

                if file_path in source_file_set:
                    file_changes[file_path].append(
                        {
                            "sha": commit_summary["sha"],
                            "author": author,
                            "date": change_date,
                        }
                    )

        page += 1

    if not repository_commit_dates:
        raise RuntimeError("No commits were returned for the repository.")

    repository_start_date = min(repository_commit_dates)
    return file_changes, repository_start_date


def build_output(
    repository,
    branch,
    source_files,
    file_changes,
    repository_start_date,
):
    """
    Convert raw change events into a documented JSON structure.

    Both detailed events and summarized author totals are retained. Detailed
    events support plotting by week, while summaries support management-level
    findings about ownership and concentration.
    """
    files = []

    for file_path in source_files:
        changes = file_changes[file_path]
        author_counts = Counter(
            change["author"] for change in changes
        )

        authors = [
            {
                "author": author,
                "touches": touches,
            }
            for author, touches in sorted(
                author_counts.items(),
                key=lambda item: (-item[1], item[0].lower()),
            )
        ]

        files.append(
            {
                "path": file_path,
                "touches": len(changes),
                "authors": authors,
                "changes": sorted(
                    changes,
                    key=lambda change: change["date"],
                ),
            }
        )

    return {
        "repository": repository,
        "default_branch": branch,
        "repository_start_date": repository_start_date,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_extensions": sorted(SOURCE_EXTENSIONS),
        "files": files,
    }


def write_json(output_data):
    """Write readable, UTF-8 JSON for later analysis and visualization."""
    DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as json_file:
        json.dump(
            output_data,
            json_file,
            indent=2,
            ensure_ascii=False,
        )
        json_file.write("\n")


def main():
    """Run the complete author and file-touch collection process."""
    default_branch = get_default_branch(REPOSITORY)
    print(f"Default branch: {default_branch}")

    source_files = collect_source_files(
        REPOSITORY,
        default_branch,
    )
    print(f"Collecting history for {len(source_files)} source files.")

    file_changes, repository_start_date = collect_file_history(
        REPOSITORY,
        default_branch,
        source_files,
    )

    output_data = build_output(
        REPOSITORY,
        default_branch,
        source_files,
        file_changes,
        repository_start_date,
    )
    write_json(output_data)

    total_touches = sum(
        file_data["touches"]
        for file_data in output_data["files"]
    )

    unique_authors = {
        change["author"]
        for file_data in output_data["files"]
        for change in file_data["changes"]
    }

    print(f"Output written to: {OUTPUT_FILE}")
    print(f"Total selected-file touches: {total_touches}")
    print(f"Unique authors: {len(unique_authors)}")


if __name__ == "__main__":
    main()