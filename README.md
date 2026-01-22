# How this works

This repository is a small experiment in managing GitHub organization teams via a YAML file, without giving up the normal GitHub UI.

The idea is:

* `teams.yaml` is a human-readable view of desired team membership

* Changes can happen either by admins in the GitHub UI or by editing the YAML (preferred)

* GitHub Actions keep the two in sync, with pull requests for visibility

# Workflows

There are three lightweight workflows:

* **GitHub → YAML** (export), Periodically reads the manually-changed org teams from GitHub, Opens a PR updating teams.yaml

* **YAML → GitHub** (apply), Runs when teams.yaml is changed. Adds/removes users from teams to match the file. Invites users to the org when needed

* **Validation** (PR check), Runs on pull requests that modify teams.yaml. Validates that all GitHub usernames exist and warns if users are not yet org members


# Current features

* Validates GitHub usernames in pull requests before merging
* Manages inclusion/exclusion for teams in an organization
* Manages invites for non-org members and team inclusion (when sync is run)
  
* GitHub → YAML is run hourly or upon manual dispatch. If changes are detected, a PR is triggered. 

* YAML → GitHub is run when `teams.yaml` is changed in the `main` branch.

# Reusing this Template in Your Organization

This repository can be used as a template to manage team memberships in your own GitHub organization. Follow these steps to set it up:

> **⚠️ IMPORTANT SAFETY NOTE:** After copying this template, you **MUST** clear the `teams.yaml` file before setting up secrets or enabling workflows. The template contains team data from the original organization. If the `teams.yaml → GitHub` workflow runs with this data, it could invite incorrect users to your organization.

## 1. Copy the Template Repository and Clear Sample Data

1. Click the "Use this template" button at the top of this repository (or fork it)
2. **Immediately** edit `teams.yaml` in your new repository and replace its contents with:
   ```yaml
   teams: {}
   ```
   This prevents the workflow from applying the original organization's team structure to your organization.

## 2. Create and Configure a GitHub App

> **Note:** These instructions are **PROVISIONAL**. A GitHub Marketplace app for simplified authorization workflow setup is currently being developed. Once available, you'll be able to install the app directly instead of creating your own.

The workflows require a GitHub App to authenticate and manage teams on behalf of your organization. This is necessary because the standard `GITHUB_TOKEN` has limited permissions for organization management.

### Creating the GitHub App

1. Go to your organization settings > Developer settings > GitHub Apps (the URL will be: `https://github.com/organizations/YOUR_ORG/settings/apps` - replace `YOUR_ORG` with your organization name)
2. Click **"New GitHub App"**
3. Configure the app with these settings:
   - **GitHub App name**: Choose a name (e.g., "Team Management Bot")
   - **Homepage URL**: Use your repository URL
   - **Webhook**: Uncheck "Active" (not needed)
   - **Permissions** (Repository permissions):
     - Contents: Read and write
     - Pull requests: Read and write
   - **Permissions** (Organization permissions):
     - Members: Read and write
     - Administration: Read (to list teams)
   - **Where can this GitHub App be installed?**: Only on this account
4. Click **"Create GitHub App"**

### Generating and Storing Credentials

After creating the app:

1. **Generate a private key**:
   - On the app settings page, scroll to "Private keys"
   - Click **"Generate a private key"**
   - Save the downloaded `.pem` file securely

2. **Note the App ID**:
   - Find the App ID near the top of the app settings page

3. **Install the app on your organization**:
   - Click **"Install App"** in the left sidebar
   - Select your organization
   - Choose "All repositories" or select specific repositories (including your team-management repo)
   - Click **"Install"**

## 3. Configure Repository Secrets

Add the GitHub App credentials as repository secrets:

1. Go to your repository settings > Secrets and variables > Actions > Repository secrets (the URL will be: `https://github.com/YOUR_ORG/team-management/settings/secrets/actions` - replace with your org and repo names)
2. Click **"New repository secret"** and add:
   - **Name**: `GH_APP_ID`
   - **Value**: Your GitHub App ID (from step 2)
3. Click **"New repository secret"** again and add:
   - **Name**: `GH_APP_PRIVATE_KEY`
   - **Value**: The entire contents of the `.pem` file (including `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----` lines)

## 4. Set Up Your Teams

**Important**: Teams must already exist in your GitHub organization before you can manage their membership with this tool. Create any needed teams in the GitHub UI (under Organization Settings → Teams) before proceeding. The workflows manage team membership, not team creation.

### Export Your Current Team Structure

Once you have teams configured in GitHub:

1. Manually trigger the **"GitHub → YAML"** workflow to export your current team structure:
   - Go to the **Actions** tab in your repository
   - Select the **"GitHub settings → teams.yaml sync"** workflow from the left sidebar
   - Click **"Run workflow"** dropdown (on the right)
   - Click the green **"Run workflow"** button
   
2. Wait for the workflow to complete (check the Actions tab for status)

3. The workflow will automatically create a pull request with your current team memberships exported to `teams.yaml`

4. Review the PR to ensure the exported data looks correct

5. Merge the PR to establish `teams.yaml` as your source of truth

## 5. Regular Usage

Once set up, the repository will:

- **Automatically export** team changes made in GitHub UI (runs hourly via cron)
- **Automatically apply** changes when you merge PRs that modify `teams.yaml`
- **Validate** team member usernames in pull requests before merging

### Making Team Changes

**Method 1: Edit `teams.yaml` (Recommended)**

1. Create a branch and edit `teams.yaml`
2. Open a pull request
3. The validation workflow will check that all usernames are valid
4. Merge the PR
5. The sync workflow will automatically update GitHub teams

**Method 2: Use GitHub UI**

1. Make changes directly in the GitHub teams UI
2. Wait for the next hourly sync (or manually trigger the "GitHub → YAML" workflow)
3. Review and merge the auto-generated PR

### Manual Workflow Triggers

All workflows can be manually triggered from the Actions tab:

- **GitHub → YAML**: Export current GitHub teams to `teams.yaml`
- **YAML → GitHub**: Apply `teams.yaml` to GitHub (normally runs on push to main)
- **Validation**: Validate `teams.yaml` (normally runs on PRs)

## Troubleshooting

- **Workflows fail with authentication errors**: Check that your GitHub App is installed on the organization and repository secrets are configured correctly
- **Teams not syncing**: Ensure the teams already exist in your organization (create them in GitHub UI first)
- **Permission errors**: Verify your GitHub App has the required organization and repository permissions
