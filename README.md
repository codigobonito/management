# How this works

This repository is a small experiment in managing GitHub organization teams via a YAML file, without giving up the normal GitHub UI.

The idea is:

* teams.yaml is a human-readable view of desired team membership

* Changes can happen either in the GitHub UI by admins or by editing the YAML (preferred)

* GitHub Actions keep the two in sync, with pull requests for visibility

# Workflows

There are two lightweight workflows:

* GitHub → YAML (export), periodically reads the manually-changed org teams from GitHub, Opens a PR updating teams.yaml

* YAML → GitHub (apply), Runs when teams.yaml is changed. Adds/removes users from teams to match the file. Invites users to the org when needed

# Current features

* Manages inclusion/exclusion for teams in an organization
* Manages invites for non-org members and team inclusion (when sync is run)
* Synchronization workflows are run daily, upon manual dispatch or when `teams.yaml` is changed
