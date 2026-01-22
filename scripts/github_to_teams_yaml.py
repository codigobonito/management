import os
from pathlib import Path

import requests
import yaml

API = "https://api.github.com"
COMMENT = "# AUTOMATICALLY UPDATED — DO NOT EDIT THIS SECTION MANUALLY\n"
MARKER = "invite_sent:"


def main():
    org = os.environ["ORG"]
    token = os.environ["TOKEN"]

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Load existing YAML (desired team organization intent + previous invite_sent)
    teams_path = Path("teams.yaml")
    try:
        old_text = teams_path.read_text(encoding="utf-8")
        old_cfg = yaml.safe_load(old_text) or {}
    except FileNotFoundError:
        old_text = ""
        old_cfg = {}

    old_desired = old_cfg.get("teams") if isinstance(old_cfg.get("teams"), dict) else {}

    # Normalize old desired (strings only)
    old_desired = {
        slug: [u.strip() for u in (users or []) if isinstance(u, str) and u.strip()]
        for slug, users in old_desired.items()
    }

    # Current org members + pending invites
    members = paginate(f"{API}/orgs/{org}/members", headers)
    org_members = {m["login"] for m in members if "login" in m}

    invs = paginate(f"{API}/orgs/{org}/invitations", headers)
    pending_invites = {i.get("login") for i in invs if i.get("login")}

    # Export current GitHub team memberships
    teams = paginate(f"{API}/orgs/{org}/teams", headers)
    teams_map = {}

    for t in sorted(teams, key=lambda x: x["slug"]):
        slug = t["slug"]
        members = paginate(f"{API}/orgs/{org}/teams/{slug}/members", headers)
        gh_logins = {m["login"] for m in members if "login" in m}

        # Preserve YAML-desired users that are pending invites (so export doesn't delete them)
        preserve = {
            u
            for u in old_desired.get(slug, [])
            if u in pending_invites and u not in org_members
        }

        teams_map[slug] = sorted(gh_logins | preserve)

    # Recompute invite_sent as status:
    # users desired somewhere AND currently pending invite AND not yet org members
    desired_all = set()
    for users in teams_map.values():
        desired_all.update(users)

    invite_sent = sorted((desired_all & pending_invites) - org_members)

    doc = {"teams": teams_map, "invite_sent": invite_sent}

    new_text = yaml.safe_dump(doc, sort_keys=True, default_flow_style=False)
    if MARKER in new_text:
        new_text = new_text.replace(MARKER, COMMENT + MARKER, 1)

    teams_path.write_text(new_text, encoding="utf-8")

    print(
        f"Wrote teams.yaml with {len(teams_map)} teams; invite_sent={len(invite_sent)}."
    )


def paginate(url, headers):
    out, page = [], 1
    while True:
        r = requests.get(
            url, headers=headers, params={"per_page": 100, "page": page}, timeout=60
        )
        r.raise_for_status()
        batch = r.json()
        out.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return out


if __name__ == "__main__":
    main()
