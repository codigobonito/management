import os
import sys
from pathlib import Path

import requests
import yaml

API = "https://api.github.com"
COMMENT = "# AUTOMATICALLY UPDATED \u2014 DO NOT EDIT THIS SECTION MANUALLY\n"
MARKER = "invite_sent:"


def main():
    org = os.environ["ORG"]
    token = os.environ["TOKEN"]

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    teams_path = Path("teams.yaml")
    old_text = teams_path.read_text(encoding="utf-8")

    cfg = yaml.safe_load(old_text) or {}
    desired = cfg.get("teams")
    if not isinstance(desired, dict):
        die("teams.yaml must contain a mapping 'teams: {team_slug: [user, ...]}'")

    # normalize desired list entries
    desired = {
        slug: [u.strip() for u in (users or []) if isinstance(u, str) and u.strip()]
        for slug, users in desired.items()
    }

    # Read current org members
    members = paginate(f"{API}/orgs/{org}/members", headers)
    org_members = {m["login"] for m in members if "login" in m}

    # Pending org invitations (logins)
    invs = paginate(f"{API}/orgs/{org}/invitations", headers)
    pending_invites = {i.get("login") for i in invs if i.get("login")}

    # Teams that exist
    teams = paginate(f"{API}/orgs/{org}/teams", headers)
    existing_slugs = {t["slug"] for t in teams if "slug" in t}

    # All desired users across all teams
    desired_all = set()
    for users in desired.values():
        desired_all.update(users)

    # Track invites we sent this run
    invited_this_run = set()

    # Apply membership per team
    for slug, users in sorted(desired.items()):
        if slug not in existing_slugs:
            die(f"Team slug '{slug}' does not exist in org '{org}'")

        want = set(users)

        # Invite any desired users not yet in org
        for u in sorted(want):
            if u in org_members:
                continue
            if u in pending_invites:
                continue
            # create invite
            if invite_by_login(org, u, headers):
                invited_this_run.add(u)

        # Now enforce team membership for org members only
        current_members = paginate(f"{API}/orgs/{org}/teams/{slug}/members", headers)
        have = {m["login"] for m in current_members if "login" in m}

        # Only org members can be in teams; want may include non-members but they won't be in have anyway
        to_add = sorted((want & org_members) - have)
        to_remove = sorted(have - want)

        for u in to_add:
            url = f"{API}/orgs/{org}/teams/{slug}/memberships/{u}"
            r = requests.put(url, headers=headers, timeout=60)
            if r.status_code >= 400:
                die(f"Failed adding {u} to {slug}: {r.status_code} {r.text}")
            print(f"ADD {slug}: {u}")

        for u in to_remove:
            url = f"{API}/orgs/{org}/teams/{slug}/memberships/{u}"
            r = requests.delete(url, headers=headers, timeout=60)
            if r.status_code >= 400:
                die(f"Failed removing {u} from {slug}: {r.status_code} {r.text}")
            print(f"REMOVE {slug}: {u}")

    # Recompute invite_sent as a *status cache*:
    # desired users who are not org members, but have a pending invite (or were invited this run)
    new_invite_sent = sorted(
        ((pending_invites | invited_this_run) & desired_all) - org_members
    )

    # Update YAML structure
    cfg["teams"] = desired
    cfg["invite_sent"] = new_invite_sent

    # Dump YAML then inject comment before invite_sent
    new_text = yaml.safe_dump(cfg, sort_keys=True, default_flow_style=False)

    if MARKER in new_text:
        new_text = new_text.replace(MARKER, COMMENT + MARKER, 1)

    changed = new_text != old_text
    if changed:
        teams_path.write_text(new_text, encoding="utf-8")

    # Expose whether we changed the file for the PR step
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"teams_yaml_changed={'true' if changed else 'false'}\n")

    print("Done.")


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


def die(msg):
    print(msg, file=sys.stderr)
    raise SystemExit(2)


def get_user_id(login, headers):
    r = requests.get(f"{API}/users/{login}", headers=headers, timeout=60)
    if r.status_code == 404:
        die(f"Unknown GitHub user: {login}")
    r.raise_for_status()
    uid = r.json().get("id")
    if not uid:
        die(f"Could not resolve user id for {login}")
    return int(uid)


def invite_by_login(org, login, headers):
    uid = get_user_id(login, headers)
    r = requests.post(
        f"{API}/orgs/{org}/invitations",
        headers=headers,
        json={"invitee_id": uid},
        timeout=60,
    )
    if r.status_code == 201:
        print(f"INVITED: {login}")
        return True
    if r.status_code == 422:
        # already invited / already a member / etc.
        try:
            msg = r.json().get("message", r.text)
        except Exception:
            msg = r.text
        print(f"INVITE SKIPPED: {login} -> {msg}")
        return False
    die(f"Invite failed for {login}: {r.status_code} {r.text}")


if __name__ == "__main__":
    main()
