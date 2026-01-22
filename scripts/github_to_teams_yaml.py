import os
from pathlib import Path

import requests
import yaml

API = "https://api.github.com"
API_VERSION = "2022-11-28"
PER_PAGE = 100
REQUEST_TIMEOUT = 60
COMMENT = "# AUTOMATICALLY UPDATED \u2014 DO NOT EDIT THIS SECTION MANUALLY\n"
MARKER = "invite_sent:"


def main():
    org = require_env("ORG")
    token = require_env("TOKEN")
    headers = auth_headers(token)

    teams_path = Path("teams.yaml")
    old_desired = load_previous_desired(teams_path)

    org_members, pending_invites = fetch_org_membership(org, headers)
    teams_map = export_teams(org, headers, old_desired, org_members, pending_invites)

    invite_sent = compute_invite_sent(teams_map, pending_invites, org_members)
    new_text = render_yaml(teams_map, invite_sent)
    teams_path.write_text(new_text, encoding="utf-8")

    print(f"Wrote teams.yaml with {len(teams_map)} teams; invite_sent={len(invite_sent)}.")


def require_env(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing required env var: {name}")
    return value


def auth_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
    }


def load_previous_desired(path):
    try:
        old_text = path.read_text(encoding="utf-8")
        old_cfg = yaml.safe_load(old_text) or {}
    except FileNotFoundError:
        old_cfg = {}

    # Preserve prior intent so pending invites aren't dropped during export.
    desired = old_cfg.get("teams") if isinstance(old_cfg.get("teams"), dict) else {}
    return {slug: normalize_users(users) for slug, users in desired.items()}


def normalize_users(users):
    return [u.strip() for u in (users or []) if isinstance(u, str) and u.strip()]


def fetch_org_membership(org, headers):
    members = paginate(f"{API}/orgs/{org}/members", headers)
    org_members = {m["login"] for m in members if "login" in m}

    invites = paginate(f"{API}/orgs/{org}/invitations", headers)
    pending_invites = {i.get("login") for i in invites if i.get("login")}

    return org_members, pending_invites


def export_teams(org, headers, old_desired, org_members, pending_invites):
    teams = paginate(f"{API}/orgs/{org}/teams", headers)
    teams_map = {}

    for team in sorted(teams, key=lambda x: x["slug"]):
        slug = team["slug"]
        members = paginate(f"{API}/orgs/{org}/teams/{slug}/members", headers)
        gh_logins = {m["login"] for m in members if "login" in m}

        # Preserve YAML-desired users that are pending invites (so export doesn't delete them).
        preserve = {
            u
            for u in old_desired.get(slug, [])
            if u in pending_invites and u not in org_members
        }

        teams_map[slug] = sorted(gh_logins | preserve)

    return teams_map


def compute_invite_sent(teams_map, pending_invites, org_members):
    desired_all = set()
    for users in teams_map.values():
        desired_all.update(users)

    # invite_sent tracks desired users who are still pending org invites.
    return sorted((desired_all & pending_invites) - org_members)


def render_yaml(teams_map, invite_sent):
    doc = {"teams": teams_map, "invite_sent": invite_sent}
    new_text = yaml.safe_dump(doc, sort_keys=True, default_flow_style=False)
    if MARKER in new_text:
        # Inject a warning comment without changing the YAML structure.
        new_text = new_text.replace(MARKER, COMMENT + MARKER, 1)
    return new_text


def paginate(url, headers):
    # GitHub REST pagination: keep fetching until the short page.
    out, page = [], 1
    while True:
        r = requests.get(
            url,
            headers=headers,
            params={"per_page": PER_PAGE, "page": page},
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        batch = r.json()
        out.extend(batch)
        if len(batch) < PER_PAGE:
            break
        page += 1
    return out


if __name__ == "__main__":
    main()
