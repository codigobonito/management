# YAML-Based Team Management

Control organization teams from a single `teams.yaml` file. 

# Workflow 

* Changes to `team.yaml` on the `main` branch triggers workflow run. YAML becomes the ground truth, GitHub settings mirror it. 

* Manual changes to the settings are checked on an hourly basis. If there is a difference, a PR is created. 

# Setup
To set up, an OWNER of the _organization_ must give the adequate access levels to an GitHub App and set up the repository secrets. 

After tokens are set, anyone with ADMIN/WRITE access to the _repository_ will be able to change teams and invite people to the org. 

## 1. Copy the Template Repository

1. Click the "Use this template" button at the top of this repository (or fork it)

## 2. Set up tokens via a personal GitHub App

The workflows require a GitHub App to authenticate and manage teams on behalf of your organization without giving it an owners' Personal Access Token (PAT). This is [a standard workflow](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/making-authenticated-api-requests-with-a-github-app-in-a-github-actions-workflow) for this kind of permissions. 

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

## 3. Configure Repository Secrets

Add the GitHub App credentials as repository secrets:

1. Go to your repository settings > Secrets and variables > Actions > Repository secrets (the URL will be: `https://github.com/YOUR_ORG/management/settings/secrets/actions` - replace with your org and repo names)
2. Click **"New repository secret"** and add:
   - **Name**: `GH_APP_ID`
   - **Value**: Your GitHub App ID (from step 2)
3. Click **"New repository secret"** again and add:
   - **Name**: `GH_APP_PRIVATE_KEY`
   - **Value**: The entire contents of the `.pem` file (including `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----` lines)

## Export Your Current Team Structure

Once you have a prelimilary team structured configured in GitHub, manually trigger the **"GitHub → YAML"** workflow to export your current team structure:
   - Go to the **Actions** tab in your repository
   - Select and run the **"GitHub settings → teams.yaml sync"** workflow from the left sidebar

## Usage

Once set up, the repository will:

- **Automatically export** team changes made in GitHub UI (runs hourly via cron)
- **Automatically apply** changes when you merge PRs that modify `teams.yaml`

It is good to protect the `main` branch and only allow changes to `teams.yaml` via a Pull Request + merge workflow, but any changes to the file will trigger the new settings in the org. 

Make sure you trust anyone with _repository_ write permissions to modify the teams in the organization and invite new people. 

## Troubleshooting

If you have some trouble using the workflow, please report it at the [GitHub issue tracker](https://github.com/codigobonito/management). 
# Features

## Implemented 

* Include/exclude people from teams that exist (even if the people are not in the org)
* Manage invites for non-org members and auto team inclusion (when sync is run)
* Validate GitHub usernames in pull requests before merging

## **Not** implemented 

Some might be implemented if (1) there is a need and (2) they are secure: 

* Create/Remove teams
* Remove people from the organization
* Change permissions of individual people or teams
* Handle team nesting

# Notes

* Users not in the org will be assigned to a list. After they accept the invitation, they will be added to the correct teams on the hourly sync workflow. 
* Teams not listed in the YAML file will be simply ignored (not deleted nor emptied)

# Development

## Running Tests

See [tests/README.md](tests/README.md) for more details on the test suite.
