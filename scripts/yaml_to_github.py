# This script considers teams.yaml as the ground truth
# and updates the GitHub organization settings accordingly.

import os
import sys
from pathlib import Path

import requests
import yaml
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API = "https://api.github.com"
API_VERSION = "2022-11-28"
PER_PAGE = 100
REQUEST_TIMEOUT = 60
COMMENT = "# AUTOMATICALLY UPDATED \u2014 DO NOT EDIT THIS SECTION MANUALLY\n"
MARKER = "invite_sent:"

# Retry configuration for API calls
RETRY_TOTAL = 3
RETRY_BACKOFF_FACTOR = 1
RETRY_STATUS_FORCELIST = [429, 500, 502, 503, 504]


def main():
    org = require_env("ORG")
    token = require_env("TOKEN")
    session = create_session(token)

    teams_path = Path("teams.yaml")
    config, desired, old_text = load_desired_teams(teams_path)

    org_members, pending_invites, existing_slugs = fetch_org_state(org, session)
    invited_this_run = apply_memberships(
        org,
        session,
        desired,
        org_members,
        pending_invites,
        existing_slugs,
    )

    new_text = render_yaml(
        config, desired, org_members, pending_invites, invited_this_run
    )
    changed = new_text != old_text
    if changed:
        teams_path.write_text(new_text, encoding="utf-8")
    else:
        print("No changes to teams.yaml needed.")

    write_changed_output(changed)
    print("Done.")


def require_env(name):
    value = os.environ.get(name)
    if not value:
        fail(f"Missing required env var: {name}")
    return value


def auth_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
    }


def create_session(token):
    """Create a requests session with retry logic and exponential backoff."""
    session = requests.Session()
    retries = Retry(
        total=RETRY_TOTAL,
        backoff_factor=RETRY_BACKOFF_FACTOR,
        status_forcelist=RETRY_STATUS_FORCELIST,
        respect_retry_after_header=True
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.headers.update(auth_headers(token))
    return session


def load_desired_teams(path):
    old_text = path.read_text(encoding="utf-8")
    config = yaml.safe_load(old_text) or {}

    # Keep the full config so other keys round-trip unchanged.
    desired = config.get("teams")
    if not isinstance(desired, dict):
        fail("teams.yaml must contain a mapping 'teams: {team_slug: [user, ...]}'")

    normalized = {slug: normalize_users(users) for slug, users in desired.items()}
    return config, normalized, old_text


def normalize_users(users):
    return [u.strip() for u in (users or []) if isinstance(u, str) and u.strip()]


def fetch_org_state(org, session):
    members = paginate(f"{API}/orgs/{org}/members", session)
    org_members = {m["login"] for m in members if "login" in m}

    invites = paginate(f"{API}/orgs/{org}/invitations", session)
    pending_invites = {i.get("login") for i in invites if i.get("login")}

    teams = paginate(f"{API}/orgs/{org}/teams", session)
    existing_slugs = {t["slug"] for t in teams if "slug" in t}

    return org_members, pending_invites, existing_slugs


def apply_memberships(
    org, session, desired, org_members, pending_invites, existing_slugs
):
    invited_this_run = set()

    for slug, users in sorted(desired.items()):
        if slug not in existing_slugs:
            fail(f"Team slug '{slug}' does not exist in org '{org}'")

        want = set(users)
        invited_this_run.update(
            invite_missing_members(org, session, want, org_members, pending_invites)
        )

        current_members = paginate(f"{API}/orgs/{org}/teams/{slug}/members", session)
        have = {m["login"] for m in current_members if "login" in m}
        reconcile_team(org, session, slug, want, have, org_members)

    return invited_this_run


def invite_missing_members(org, session, want, org_members, pending_invites):
    invited = set()
    for login in sorted(want):
        # Avoid duplicate invites by skipping members and pending invites.
        if login in org_members or login in pending_invites:
            continue
        if invite_by_login(org, login, session):
            invited.add(login)
    return invited


def reconcile_team(org, session, slug, want, have, org_members):
    # Only org members can be added to teams.
    to_add = sorted((want & org_members) - have)
    to_remove = sorted(have - want)

    for login in to_add:
        url = f"{API}/orgs/{org}/teams/{slug}/memberships/{login}"
        r = session.put(url, timeout=REQUEST_TIMEOUT)
        if r.status_code >= 400:
            fail(f"Failed adding {login} to {slug}: {r.status_code} {r.text}")
        print(f"ADD {slug}: {login}")

    for login in to_remove:
        url = f"{API}/orgs/{org}/teams/{slug}/memberships/{login}"
        r = session.delete(url, timeout=REQUEST_TIMEOUT)
        if r.status_code >= 400:
            fail(f"Failed removing {login} from {slug}: {r.status_code} {r.text}")
        print(f"REMOVE {slug}: {login}")


def render_yaml(config, desired, org_members, pending_invites, invited_this_run):
    desired_all = set()
    for users in desired.values():
        desired_all.update(users)

    # invite_sent is a status cache: desired users with pending invites and no membership yet.
    invite_sent = sorted(
        ((pending_invites | invited_this_run) & desired_all) - org_members
    )

    config["teams"] = desired
    config["invite_sent"] = invite_sent

    new_text = yaml.safe_dump(config, sort_keys=True, default_flow_style=False)
    if MARKER in new_text:
        # Inject a warning comment without changing the YAML structure.
        new_text = new_text.replace(MARKER, COMMENT + MARKER, 1)
    return new_text


def write_changed_output(changed):
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        # Let downstream workflow steps know whether teams.yaml was updated.
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"teams_yaml_changed={'true' if changed else 'false'}\n")


def paginate(url, session):
    # GitHub REST pagination: keep fetching until the short page.
    out, page = [], 1
    while True:
        r = session.get(
            url,
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


def fail(msg):
    print(msg, file=sys.stderr)
    raise SystemExit(2)


def get_user_id(login, session):
    r = session.get(f"{API}/users/{login}", timeout=REQUEST_TIMEOUT)
    if r.status_code == 404:
        fail(f"Unknown GitHub user: {login}")
    r.raise_for_status()
    uid = r.json().get("id")
    if not uid:
        fail(f"Could not resolve user id for {login}")
    return int(uid)


def invite_by_login(org, login, session):
    uid = get_user_id(login, session)
    r = session.post(
        f"{API}/orgs/{org}/invitations",
        json={"invitee_id": uid},
        timeout=REQUEST_TIMEOUT,
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
    fail(f"Invite failed for {login}: {r.status_code} {r.text}")


if __name__ == "__main__":
    main()
