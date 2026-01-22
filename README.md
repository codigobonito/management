# How this works

This repository is a small experiment in managing GitHub organization teams via a YAML file, without giving up the normal GitHub UI.

The idea is:

* teams.yaml is a human-readable view of desired team membership

* Changes can happen either in the GitHub UI by admins or by editing the YAML (preferred)

* GitHub Actions keep the two in sync, with pull requests for visibility

# Workflows

There are four lightweight workflows:

* **Validation** (PR check), Runs on pull requests that modify teams.yaml. Validates that all GitHub usernames exist and warns if users are not yet org members

* **Manual PR Validation**, Manually triggered workflow to validate any PR (including those created by GitHub Actions). Go to Actions → Manual PR Validation → Run workflow, and enter the PR number to validate

* **GitHub → YAML** (export), Periodically reads the manually-changed org teams from GitHub, Opens a PR updating teams.yaml

* **YAML → GitHub** (apply), Runs when teams.yaml is changed. Adds/removes users from teams to match the file. Invites users to the org when needed

# Current features

* Validates GitHub usernames in pull requests before merging
* Manages inclusion/exclusion for teams in an organization
* Manages invites for non-org members and team inclusion (when sync is run)
* Synchronization workflows are run daily, upon manual dispatch or when `teams.yaml` is changed
* Manual validation workflow allows checking PRs created by GitHub Actions (automated checks don't run on these PRs due to GitHub's security restrictions)

# Using Manual PR Validation

When the automated export workflow creates a PR, GitHub's security model prevents the validation workflow from running automatically. To validate these PRs before merging:

1. Go to the **Actions** tab in the repository
2. Select **Manual PR Validation** from the workflows list
3. Click **Run workflow**
4. Enter the PR number in the input field
5. Click **Run workflow** to start the validation

The workflow will validate the `teams.yaml` file and post a comment on the PR with the results. If validation passes, it's safe to merge the PR.
