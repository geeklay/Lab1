"""
Collect source files from the scottyab/rootbeer repository.

Assignment scope
----------------
This script adapts the provided CollectFiles.py starter script to:

1. Read GitHub credentials securely from an environment variable.
2. Discover the repository's default branch instead of assuming "main."
3. Select only source files using a documented extension-based definition.
4. Exclude documentation, images, configuration, generated output, and
   compiled artifacts.
5. Count how many commits touched each selected source file.
6. Produce a username-specific CSV so team members do not overwrite one
   another's results.

Source-file definition
----------------------
For this analysis, a source file is authored implementation, header, or test
code with one of these extensions:

    .java, .kt, .cpp, .c, .h

Tests are included because they are maintained executable source code. Build
configuration, documentation, images, compiled files, and generated output are
excluded.

Limitation
----------
Extension-based filtering can miss source code written in an unlisted language
and could include generated code if it uses a recognized extension.
"""

import csv
import os
from pathlib import Path

import requests


# The assignment specifically requires analysis of this public repository.
REPOSITORY = "scottyab/rootbeer"

# Rootbeer currently contains Java, Kotlin, C++, and C-related code.
# Headers are included because they are part of the native implementation.
SOURCE_EXTENSIONS = {".java", ".kt", ".cpp", ".c", ".h"}

# Build paths relative to this script rather than the current terminal
# directory. This keeps all generated files inside repo_mining/data even when
# the script is launched from the repository root.
SCRIPT_DIRECTORY = Path(__file__).resolve().parent
DATA_DIRECTORY = SCRIPT_DIRECTORY / "data"

# The username prefix prevents collisions with teammates' generated data.
OUTPUT_FILE = DATA_DIRECTORY / "kenner1-unlv_file_rootbeer.csv"

# A shared API base keeps endpoint construction consistent and readable.
API_BASE_URL = "https://api.github.com"


def create_headers():
    """
    Create authenticated GitHub API headers.

    The starter script stored tokens directly in source code. The assignment
    prohibits credentials in source files, commits, reports, and screenshots,
    so this version reads the token from GITHUB_TOKEN at runtime.
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
    """
    Request and return JSON data from GitHub.

    The starter script suppressed many exceptions, which could produce
    incomplete results without explaining why. raise_for_status() makes API,
    authentication, and rate-limit failures visible.
    """
    response = requests.get(
        url,
        headers=create_headers(),
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_default_branch(repository):
    """
    Discover the repository's default branch through GitHub.

    The assignment explicitly says not to assume the branch is named "main."
    Rootbeer's current default branch is "master," but the script discovers
    that value dynamically so it remains correct if the repository changes.
    """
    repository_data = github_get(
        f"{API_BASE_URL}/repos/{repository}"
    )
    return repository_data["default_branch"]


def is_source_file(file_path):
    """
    Determine whether a repository path satisfies our source definition.

    Path.suffix extracts the final extension, and lower() makes matching
    case-insensitive.
    """
    return Path(file_path).suffix.lower() in SOURCE_EXTENSIONS


def collect_source_files(repository, branch):
    """
    Collect source files currently present on the default branch.

    A recursive Git tree provides the complete current file structure in one
    request. Only blob entries represent files; directories are excluded.
    """
    tree_data = github_get(
        f"{API_BASE_URL}/repos/{repository}/git/trees/{branch}",
        params={"recursive": "1"},
    )

    # GitHub can truncate very large recursive trees. Silently accepting a
    # truncated response would make the analysis incomplete.
    if tree_data.get("truncated"):
        raise RuntimeError(
            "GitHub returned a truncated repository tree; "
            "the source-file list may be incomplete."
        )

    source_files = sorted(
        item["path"]
        for item in tree_data["tree"]
        if item["type"] == "blob" and is_source_file(item["path"])
    )

    if not source_files:
        raise RuntimeError(
            "No files matched the documented source-file extensions."
        )

    return source_files


def count_file_touches(repository, branch, source_files):
    """
    Count commits that touched each currently selected source file.

    GitHub returns commits in pages. The loop continues until an empty page is
    returned, ensuring that the analysis covers the repository's full default-
    branch history rather than only the first 30 or 100 commits.
    """
    touches = {file_path: 0 for file_path in source_files}
    page = 1

    while True:
        commits = github_get(
            f"{API_BASE_URL}/repos/{repository}/commits",
            params={
                # Restrict history to the dynamically discovered default
                # branch, as required by the assignment.
                "sha": branch,
                "page": page,
                "per_page": 100,
            },
        )

        if not commits:
            break

        print(f"Processing commit page {page}...")

        for commit in commits:
            # The commit-list endpoint does not contain its complete changed-
            # file list, so each commit must be requested individually.
            commit_details = github_get(
                f"{API_BASE_URL}/repos/{repository}/commits/"
                f"{commit['sha']}"
            )

            for changed_file in commit_details.get("files", []):
                file_path = changed_file["filename"]

                # Count only files selected by the current source-file
                # definition. Non-source repository activity is excluded.
                if file_path in touches:
                    touches[file_path] += 1

        page += 1

    return touches


def write_source_file_csv(file_touches):
    """
    Write the selected source-file list and touch totals to a CSV file.

    Including both fields gives later scripts a reusable, structured input
    while also satisfying Task 1's requirement to produce the selected list.
    """
    DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Filename", "Touches"])

        for file_path, touch_count in sorted(file_touches.items()):
            writer.writerow([file_path, touch_count])


def main():
    """Run the complete source-file collection process."""
    default_branch = get_default_branch(REPOSITORY)
    print(f"Default branch: {default_branch}")

    source_files = collect_source_files(
        REPOSITORY,
        default_branch,
    )

    # Printing the selected paths makes the selection visible and directly
    # satisfies the requirement to produce a source-file list.
    print(f"Selected {len(source_files)} source files:")
    for file_path in source_files:
        print(f"  {file_path}")

    file_touches = count_file_touches(
        REPOSITORY,
        default_branch,
        source_files,
    )

    write_source_file_csv(file_touches)

    most_touched_file = max(
        file_touches,
        key=file_touches.get,
    )

    print(f"Output written to: {OUTPUT_FILE}")
    print(
        f"Most frequently touched source file: {most_touched_file} "
        f"({file_touches[most_touched_file]} touches)"
    )


# This guard allows the functions to be inspected or reused without
# automatically launching hundreds of GitHub API requests.
if __name__ == "__main__":
    main()