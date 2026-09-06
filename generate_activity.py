#!/usr/bin/env python3
"""
Combined Activity Map Generator
Fetches activity data from:
  1. GitHub (commits / PRs / issues via GraphQL API)
  2. LeetCode (submissions via GraphQL API)
  3. Codeforces (submissions via user.status API)
Merges them by date and generates a sleek, dark-themed SVG contribution heatmap.
"""

import datetime
import json
import os
import subprocess
import sys
from collections import defaultdict
import requests

GH_USER = "singhvi28"
LC_USER = "akshitsinghvi28"
CF_USER = "akshitsinghvi28"


def fetch_github_contributions():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    query = f"""
    query {{
      user(login: "{GH_USER}") {{
        contributionsCollection {{
          contributionCalendar {{
            totalContributions
            weeks {{
              firstDay
              contributionDays {{
                contributionCount
                date
                weekday
              }}
            }}
            months {{
              name
              firstDay
              totalWeeks
            }}
          }}
        }}
      }}
    }}
    """
    try:
        if token:
            headers = {"Authorization": f"Bearer {token}", "User-Agent": "Activity-Generator"}
            res = requests.post("https://api.github.com/graphql", json={"query": query}, headers=headers, timeout=20)
            data = res.json()
        else:
            cmd = ["gh", "api", "graphql", "-f", f"query={query}"]
            res_str = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
            data = json.loads(res_str)

        return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    except Exception as e:
        print(f"Error fetching GitHub contributions: {e}", file=sys.stderr)
        return None


def fetch_leetcode_submissions():
    query = """
    query userProfileCalendar($username: String!) {
      matchedUser(username: $username) {
        userCalendar {
          submissionCalendar
        }
      }
    }
    """
    try:
        res = requests.post(
            "https://leetcode.com/graphql",
            json={"query": query, "variables": {"username": LC_USER}},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20,
        )
        if res.status_code == 200:
            data = res.json()
            raw_str = data.get("data", {}).get("matchedUser", {}).get("userCalendar", {}).get("submissionCalendar", "{}")
            raw_dict = json.loads(raw_str)
            daily = defaultdict(int)
            for ts_str, count in raw_dict.items():
                date_str = datetime.datetime.fromtimestamp(int(ts_str), datetime.timezone.utc).strftime("%Y-%m-%d")
                daily[date_str] += count
            return daily
    except Exception as e:
        print(f"Error fetching LeetCode submissions: {e}", file=sys.stderr)
    return defaultdict(int)


def fetch_codeforces_submissions():
    try:
        res = requests.get(f"https://codeforces.com/api/user.status?handle={CF_USER}", timeout=20)
        if res.status_code == 200:
            data = res.json()
            if data.get("status") == "OK":
                daily = defaultdict(int)
                for sub in data.get("result", []):
                    ts = sub.get("creationTimeSeconds", 0)
                    date_str = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%d")
                    daily[date_str] += 1
                return daily
    except Exception as e:
        print(f"Error fetching Codeforces submissions: {e}", file=sys.stderr)
    return defaultdict(int)


def get_color(count):
    if count == 0:
        return "#161b22"
    elif count <= 2:
        return "#0e4429"
    elif count <= 5:
        return "#006d32"
    elif count <= 9:
        return "#26a641"
    else:
        return "#39d353"


def generate_svg(calendar, lc_data, cf_data, output_path="combined_activity.svg"):
    weeks = calendar["weeks"]
    months = calendar["months"]

    # Calculate totals
    total_gh = 0
    total_lc = 0
    total_cf = 0

    all_dates = set()
    for w in weeks:
        for d in w["contributionDays"]:
            dt = d["date"]
            all_dates.add(dt)
            total_gh += d["contributionCount"]

    for dt in all_dates:
        total_lc += lc_data.get(dt, 0)
        total_cf += cf_data.get(dt, 0)

    total_combined = total_gh + total_lc + total_cf

    # Layout constants
    cell_size = 11
    cell_gap = 3
    step = cell_size + cell_gap
    start_x = 42
    start_y = 86
    grid_width = len(weeks) * step
    svg_width = start_x + grid_width + 25
    svg_height = 220

    svg_parts = []
    svg_parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}" fill="none">')
    svg_parts.append('''
  <defs>
    <style>
      .bg { fill: #0d1117; stroke: #30363d; stroke-width: 1; rx: 8px; }
      .title { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 14px; font-weight: 600; fill: #f0f6fc; }
      .subtitle { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 11.5px; fill: #8b949e; }
      .badge-gh { fill: #3fb950; font-weight: 600; }
      .badge-lc { fill: #ffa116; font-weight: 600; }
      .badge-cf { fill: #58a6ff; font-weight: 600; }
      .lbl { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 10px; fill: #7d8590; }
      .cell { rx: 2px; ry: 2px; }
      .cell:hover { stroke: #ffffff; stroke-width: 1.5; }
    </style>
  </defs>
''')

    # Background Card
    svg_parts.append(f'  <rect width="{svg_width}" height="{svg_height}" class="bg" />')

    # Header Title
    svg_parts.append('  <text x="24" y="30" class="title">Merged Activity Heatmap</text>')

    # Subtitle with Breakdown
    sub_text = (
        f'<text x="24" y="52" class="subtitle">'
        f'<tspan font-weight="600" fill="#c9d1d9">{total_combined:,} Total Activities</tspan> in the last year  '
        f'•  <tspan class="badge-gh">GitHub:</tspan> {total_gh:,}  '
        f'•  <tspan class="badge-lc">LeetCode:</tspan> {total_lc:,}  '
        f'•  <tspan class="badge-cf">Codeforces:</tspan> {total_cf:,}'
        f'</text>'
    )
    svg_parts.append(f'  {sub_text}')

    # Month Labels
    month_y = start_y - 10
    prev_x = -100
    for w_idx, w in enumerate(weeks):
        first_day = w["contributionDays"][0]["date"]
        # Check if this week starts a new month
        dt_obj = datetime.datetime.strptime(first_day, "%Y-%m-%d")
        if dt_obj.day <= 7:
            x_pos = start_x + w_idx * step
            if x_pos - prev_x >= 28:
                m_name = dt_obj.strftime("%b")
                svg_parts.append(f'  <text x="{x_pos}" y="{month_y}" class="lbl">{m_name}</text>')
                prev_x = x_pos

    # Day of week labels (Mon, Wed, Fri)
    svg_parts.append(f'  <text x="14" y="{start_y + 1 * step + 9}" class="lbl">Mon</text>')
    svg_parts.append(f'  <text x="14" y="{start_y + 3 * step + 9}" class="lbl">Wed</text>')
    svg_parts.append(f'  <text x="14" y="{start_y + 5 * step + 9}" class="lbl">Fri</text>')

    # Grid Cells
    for w_idx, w in enumerate(weeks):
        for d in w["contributionDays"]:
            weekday = d["weekday"]
            date_str = d["date"]
            gh_c = d["contributionCount"]
            lc_c = lc_data.get(date_str, 0)
            cf_c = cf_data.get(date_str, 0)
            total = gh_c + lc_c + cf_c

            color = get_color(total)
            x_pos = start_x + w_idx * step
            y_pos = start_y + weekday * step

            title = f"{date_str}: {total} activities ({gh_c} GitHub, {lc_c} LeetCode, {cf_c} Codeforces)"
            svg_parts.append(
                f'  <rect x="{x_pos}" y="{y_pos}" width="{cell_size}" height="{cell_size}" fill="{color}" class="cell">'
                f'<title>{title}</title></rect>'
            )

    # Legend at bottom right
    legend_y = start_y + 7 * step + 16
    legend_end_x = start_x + grid_width
    leg_colors = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
    leg_cells_w = len(leg_colors) * step
    leg_x = legend_end_x - leg_cells_w - 38

    svg_parts.append(f'  <text x="{leg_x - 30}" y="{legend_y + 9}" class="lbl">Less</text>')
    for i, col in enumerate(leg_colors):
        cx = leg_x + i * step
        svg_parts.append(f'  <rect x="{cx}" y="{legend_y}" width="{cell_size}" height="{cell_size}" fill="{col}" class="cell" />')
    svg_parts.append(f'  <text x="{leg_x + len(leg_colors) * step + 6}" y="{legend_y + 9}" class="lbl">More</text>')

    svg_parts.append('</svg>')

    content = "\n".join(svg_parts)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated {output_path} successfully ({total_combined:,} combined activities).")


def main():
    print("Fetching GitHub contributions...")
    calendar = fetch_github_contributions()
    if not calendar:
        print("Failed to fetch GitHub calendar data.", file=sys.stderr)
        sys.exit(1)

    print("Fetching LeetCode submissions...")
    lc_data = fetch_leetcode_submissions()

    print("Fetching Codeforces submissions...")
    cf_data = fetch_codeforces_submissions()

    out_file = sys.argv[1] if len(sys.argv) > 1 else "combined_activity.svg"
    generate_svg(calendar, lc_data, cf_data, out_file)


if __name__ == "__main__":
    main()
