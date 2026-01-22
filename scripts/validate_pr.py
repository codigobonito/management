# Checks if the users in teams.yaml exist on GitHub and are members of the organization.

import os, sys, requests, yaml
from pathlib import Path

ORG = os.environ["ORG"]
TOKEN = os.environ["TOKEN"]
API = "https://api.github.com"

H = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def paginate(url):
    out, page = [], 1
    while True:
        try:
            r = requests.get(
                url, headers=H, params={"per_page": 100, "page": page}, timeout=60
            )
            r.raise_for_status()
            batch = r.json()
            out.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        except requests.exceptions.RequestException as e:
            print(f"ERROR: Failed to fetch data from GitHub API: {e}")
            sys.exit(1)
    return out


def user_exists(login: str) -> bool:
    """Check if a GitHub user exists."""
    try:
        r = requests.get(f"{API}/users/{login}", headers=H, timeout=60)
        if r.status_code == 403:
            # Check if it's a rate limit issue
            if (
                "X-RateLimit-Remaining" in r.headers
                and r.headers["X-RateLimit-Remaining"] == "0"
            ):
                print(f"ERROR: GitHub API rate limit exceeded")
                sys.exit(1)
        return r.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to check user '{login}': {e}")
        sys.exit(1)

    # Load teams.yaml
    teams_path = Path("teams.yaml")
    cfg = yaml.safe_load(teams_path.read_text(encoding="utf-8")) or {}
    desired_team_configuration = cfg.get("teams")

    if not isinstance(desired_team_configuration, dict):
        print(
            "ERROR: teams.yaml must contain a mapping 'teams: {team_slug: [user, ...]}'"
        )
        sys.exit(1)

    # Normalize desired list entries
    desired_users = {
        slug: [u.strip() for u in (users or []) if isinstance(u, str) and u.strip()]
        for slug, users in desired_team_configuration.items()
    }

    # Get all unique usernames from teams
    all_users = set()
    for users in desired_users.values():
        all_users.update(users)

    # Get current org members
    members = paginate(f"{API}/orgs/{ORG}/members")
    org_members = {m["login"] for m in members if "login" in m}

    # Validate each username
    invalid_users = []
    non_org_users = []

    for username in sorted(all_users):
        # Check if user exists on GitHub
        if not user_exists(username):
            invalid_users.append(username)
            print(f"❌ ERROR: GitHub user '{username}' does not exist")
        elif username not in org_members:
            non_org_users.append(username)
            print(
                f"⚠️  WARNING: User '{username}' exists but is not a member of the '{ORG}' organization"
            )

    # Report results
    if invalid_users:
        print(f"\n❌ Validation FAILED: {len(invalid_users)} invalid username(s) found")
        print(f"Invalid users: {', '.join(invalid_users)}")
        sys.exit(1)

    if non_org_users:
        print(
            f"\n⚠️  {len(non_org_users)} user(s) are not in the organization (invites will be sent once the PR is merged)"
        )
        print(f"Non-org users: {', '.join(non_org_users)}")

    if not invalid_users and not non_org_users:
        print("\n✅ All usernames are valid and are members of the organization")
    elif not invalid_users:
        print(
            "\n✅ All usernames are valid (some will receive org invites once the PR is merged)"
        )

    print("Validation completed successfully.")
