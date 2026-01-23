"""Tests for github_to_yaml.py script functionality."""

import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import os

# Set required environment variables before importing
os.environ['ORG'] = 'test-org'
os.environ['TOKEN'] = 'test-token'

# Add parent directory to path to import the script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import github_to_yaml


class TestGithubToYamlFunctionality(unittest.TestCase):
    """Test the main functionality of github_to_yaml script."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_session = MagicMock()
        self.org = 'test-org'

    @patch('github_to_yaml.paginate')
    def test_adding_org_member_to_team_export(self, mock_paginate):
        """Test that when an org member is added to a team in GitHub, it's exported to YAML."""
        # Setup: alice is in org and now in the developers team
        org_members = {'alice', 'bob'}
        pending_invites = set()
        old_desired = {'developers': []}  # Previously empty team
        
        # Mock paginate to return teams and team members
        def paginate_side_effect(url, session):
            if 'teams' in url and 'members' not in url:
                # Return list of teams
                return [{'slug': 'developers'}]
            elif 'members' in url:
                # Return team members - alice is now in the team
                return [{'login': 'alice'}]
            return []
        
        mock_paginate.side_effect = paginate_side_effect
        
        # Call export_teams
        teams_map = github_to_yaml.export_teams(
            self.org,
            self.mock_session,
            old_desired,
            org_members,
            pending_invites
        )
        
        # Verify alice is in the exported team
        self.assertIn('developers', teams_map)
        self.assertIn('alice', teams_map['developers'])

    @patch('github_to_yaml.paginate')
    def test_removing_member_from_team_export(self, mock_paginate):
        """Test that when a member is removed from a team in GitHub, it's removed from YAML."""
        # Setup: bob was in team but is now removed
        org_members = {'alice', 'bob'}
        pending_invites = set()
        old_desired = {'developers': ['alice', 'bob']}  # Bob was previously in team
        
        # Mock paginate to return teams and team members
        def paginate_side_effect(url, session):
            if 'teams' in url and 'members' not in url:
                # Return list of teams
                return [{'slug': 'developers'}]
            elif 'members' in url:
                # Return team members - only alice now (bob removed)
                return [{'login': 'alice'}]
            return []
        
        mock_paginate.side_effect = paginate_side_effect
        
        # Call export_teams
        teams_map = github_to_yaml.export_teams(
            self.org,
            self.mock_session,
            old_desired,
            org_members,
            pending_invites
        )
        
        # Verify bob is NOT in the exported team
        self.assertIn('developers', teams_map)
        self.assertIn('alice', teams_map['developers'])
        self.assertNotIn('bob', teams_map['developers'])

    @patch('github_to_yaml.paginate')
    def test_removing_member_from_org_export(self, mock_paginate):
        """Test that when a member is removed from the org, they're removed from all teams in YAML."""
        # Setup: charlie was in org and team, but is now removed from org
        org_members = {'alice', 'bob'}  # charlie is not in org anymore
        pending_invites = set()
        old_desired = {'developers': ['alice', 'bob', 'charlie']}
        
        # Mock paginate to return teams and team members
        def paginate_side_effect(url, session):
            if 'teams' in url and 'members' not in url:
                # Return list of teams
                return [{'slug': 'developers'}]
            elif 'members' in url:
                # Return team members - charlie is not in team (removed from org)
                return [{'login': 'alice'}, {'login': 'bob'}]
            return []
        
        mock_paginate.side_effect = paginate_side_effect
        
        # Call export_teams
        teams_map = github_to_yaml.export_teams(
            self.org,
            self.mock_session,
            old_desired,
            org_members,
            pending_invites
        )
        
        # Verify charlie is NOT in the exported team
        self.assertIn('developers', teams_map)
        self.assertIn('alice', teams_map['developers'])
        self.assertIn('bob', teams_map['developers'])
        self.assertNotIn('charlie', teams_map['developers'])

    @patch('github_to_yaml.paginate')
    def test_preserve_pending_invites_in_export(self, mock_paginate):
        """Test that users with pending invites are preserved in YAML export."""
        # Setup: dave has a pending invite and is in old desired state
        org_members = {'alice', 'bob'}
        pending_invites = {'dave'}  # dave has pending invite
        old_desired = {'developers': ['alice', 'bob', 'dave']}
        
        # Mock paginate to return teams and team members
        def paginate_side_effect(url, session):
            if 'teams' in url and 'members' not in url:
                # Return list of teams
                return [{'slug': 'developers'}]
            elif 'members' in url:
                # Return team members - only alice and bob (dave not in org yet)
                return [{'login': 'alice'}, {'login': 'bob'}]
            return []
        
        mock_paginate.side_effect = paginate_side_effect
        
        # Call export_teams
        teams_map = github_to_yaml.export_teams(
            self.org,
            self.mock_session,
            old_desired,
            org_members,
            pending_invites
        )
        
        # Verify dave is preserved in the export (because of pending invite)
        self.assertIn('developers', teams_map)
        self.assertIn('alice', teams_map['developers'])
        self.assertIn('bob', teams_map['developers'])
        self.assertIn('dave', teams_map['developers'])

    @patch('github_to_yaml.paginate')
    def test_export_multiple_teams(self, mock_paginate):
        """Test exporting multiple teams with different members."""
        org_members = {'alice', 'bob', 'charlie'}
        pending_invites = set()
        old_desired = {}
        
        # Mock paginate to return multiple teams
        def paginate_side_effect(url, session):
            if 'teams' in url and 'members' not in url:
                # Return list of teams
                return [
                    {'slug': 'developers'},
                    {'slug': 'admins'}
                ]
            elif 'developers/members' in url:
                return [{'login': 'alice'}, {'login': 'bob'}]
            elif 'admins/members' in url:
                return [{'login': 'charlie'}]
            return []
        
        mock_paginate.side_effect = paginate_side_effect
        
        # Call export_teams
        teams_map = github_to_yaml.export_teams(
            self.org,
            self.mock_session,
            old_desired,
            org_members,
            pending_invites
        )
        
        # Verify both teams are exported correctly
        self.assertIn('developers', teams_map)
        self.assertIn('admins', teams_map)
        self.assertEqual(set(teams_map['developers']), {'alice', 'bob'})
        self.assertEqual(set(teams_map['admins']), {'charlie'})


class TestFetchOrgMembership(unittest.TestCase):
    """Test the fetch_org_membership function."""

    @patch('github_to_yaml.paginate')
    def test_fetch_org_members_and_invites(self, mock_paginate):
        """Test fetching org members and pending invites."""
        org = 'test-org'
        session = MagicMock()
        
        # Mock paginate to return different data based on URL
        def paginate_side_effect(url, session):
            if '/members' in url:
                return [
                    {'login': 'alice'},
                    {'login': 'bob'}
                ]
            elif '/invitations' in url:
                return [
                    {'login': 'charlie'},
                    {'login': 'dave'}
                ]
            return []
        
        mock_paginate.side_effect = paginate_side_effect
        
        org_members, pending_invites = github_to_yaml.fetch_org_membership(org, session)
        
        # Verify members and invites are correctly fetched
        self.assertEqual(org_members, {'alice', 'bob'})
        self.assertEqual(pending_invites, {'charlie', 'dave'})

    @patch('github_to_yaml.paginate')
    def test_fetch_with_no_pending_invites(self, mock_paginate):
        """Test fetching when there are no pending invites."""
        org = 'test-org'
        session = MagicMock()
        
        def paginate_side_effect(url, session):
            if '/members' in url:
                return [{'login': 'alice'}, {'login': 'bob'}]
            elif '/invitations' in url:
                return []  # No pending invites
            return []
        
        mock_paginate.side_effect = paginate_side_effect
        
        org_members, pending_invites = github_to_yaml.fetch_org_membership(org, session)
        
        self.assertEqual(org_members, {'alice', 'bob'})
        self.assertEqual(pending_invites, set())


class TestRenderYaml(unittest.TestCase):
    """Test the render_yaml function."""

    def test_render_yaml_basic(self):
        """Test basic YAML rendering."""
        teams_map = {
            'developers': ['alice', 'bob'],
            'admins': ['charlie']
        }
        invite_sent = {'dave', 'eve'}
        
        yaml_text = github_to_yaml.render_yaml(teams_map, invite_sent)
        
        # Verify YAML contains expected sections
        self.assertIn('teams:', yaml_text)
        self.assertIn('developers:', yaml_text)
        self.assertIn('admins:', yaml_text)
        self.assertIn('invite_sent:', yaml_text)
        self.assertIn('- alice', yaml_text)
        self.assertIn('- bob', yaml_text)
        self.assertIn('- charlie', yaml_text)

    def test_render_yaml_with_comment(self):
        """Test that YAML rendering includes the auto-update comment."""
        teams_map = {'developers': ['alice']}
        invite_sent = {'bob'}
        
        yaml_text = github_to_yaml.render_yaml(teams_map, invite_sent)
        
        # Verify the comment is added
        self.assertIn('# AUTOMATICALLY UPDATED', yaml_text)
        self.assertIn('DO NOT EDIT THIS SECTION MANUALLY', yaml_text)

    def test_render_yaml_empty_invite_sent(self):
        """Test rendering with no pending invites."""
        teams_map = {'developers': ['alice', 'bob']}
        invite_sent = set()
        
        yaml_text = github_to_yaml.render_yaml(teams_map, invite_sent)
        
        self.assertIn('teams:', yaml_text)
        self.assertIn('invite_sent: []', yaml_text)


class TestLoadPreviousDesired(unittest.TestCase):
    """Test the load_previous_desired function."""

    @patch('github_to_yaml.Path')
    def test_load_existing_yaml(self, mock_path):
        """Test loading an existing teams.yaml file."""
        yaml_content = """
teams:
  developers:
    - alice
    - bob
  admins:
    - charlie
"""
        mock_path.return_value.read_text.return_value = yaml_content
        
        desired = github_to_yaml.load_previous_desired(mock_path.return_value)
        
        self.assertIn('developers', desired)
        self.assertIn('admins', desired)
        self.assertEqual(desired['developers'], ['alice', 'bob'])
        self.assertEqual(desired['admins'], ['charlie'])

    @patch('github_to_yaml.Path')
    def test_load_nonexistent_file(self, mock_path):
        """Test loading when teams.yaml doesn't exist."""
        mock_path.return_value.read_text.side_effect = FileNotFoundError()
        
        desired = github_to_yaml.load_previous_desired(mock_path.return_value)
        
        # Should return empty dict when file doesn't exist
        self.assertEqual(desired, {})

    @patch('github_to_yaml.Path')
    def test_load_empty_yaml(self, mock_path):
        """Test loading an empty YAML file."""
        mock_path.return_value.read_text.return_value = ""
        
        desired = github_to_yaml.load_previous_desired(mock_path.return_value)
        
        # Should return empty dict for empty file
        self.assertEqual(desired, {})


if __name__ == '__main__':
    unittest.main()
