import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt

repo = "scottyab/rootbeer"

repo_name = repo.split("/")[1]
json_path = f"data/mikepodo_authors_rootbeer.json"
plot_path = f"mikepodo_file_activity.png"


def parse_date(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


with open(json_path) as f:
    files_data = json.load(f)

if not files_data:
    raise SystemExit(f"No data in {json_path}")

all_dates = [
    parse_date(commit["date"])
    for file_entry in files_data
    for commit in file_entry["commits"]
]
repo_start = min(all_dates)

authors = sorted(
    {
        commit["author"]
        for file_entry in files_data
        for commit in file_entry["commits"]
    }
)
author_index = {author: i for i, author in enumerate(authors)}
cmap = plt.get_cmap("tab20")

seen = set()
weeks = []
file_indices = []
colors = []

for file_idx, file_entry in enumerate(files_data):
    for commit in file_entry["commits"]:
        author = commit.get("author") or "unknown"
        date = commit.get("date")
        if not date:
            continue
        week = (parse_date(date) - repo_start).days // 7
        key = (week, file_idx, author)
        if key in seen:
            continue
        seen.add(key)
        weeks.append(week)
        file_indices.append(file_idx)
        colors.append(cmap(author_index.get(author, 0) % 20))

fig, ax = plt.subplots(figsize=(10, 6))
# x = weeks since repo start, y = source file, color = author
ax.scatter(weeks, file_indices, c=colors, s=28, alpha=0.9, edgecolors="none")
ax.set_xlabel("weeks")
ax.set_ylabel("file")
ax.set_title(f"{repo} — file touches by author over time")
ax.set_ylim(-0.5, max(file_indices) + 0.5)
ax.set_xlim(left=-5)

fig.tight_layout()
fig.savefig(plot_path, dpi=150)
plt.close(fig)
print(f"Saved {plot_path}")
