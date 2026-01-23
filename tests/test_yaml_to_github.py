"""Tests for yaml_to_github.py script functionality."""

import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import os
from pathlib import Path

# Set required environment variables before importing
os.environ['ORG'] = 'test-org'
os.environ['TOKEN'] = 'test-token'

# Add parent directory to path to import the script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import yaml_to_github


class TestYamlToGithubFunctionality(unittest.TestCase):
    """Test the main functionality of yaml_to_github script."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_session = MagicMock()
        self.org = 'test-org'

    @patch('yaml_to_github.paginate')
    def test_adding_org_member_to_team(self, mock_paginate):
        """Test adding someone to a team who is already in the org."""
        # Setup: user is in org but not in team
        org_members = {'alice', 'bob'}
        pending_invites = set()
        existing_slugs = {'developers'}
        
        # Current team members (bob is not in the team yet)
        mock_paginate.return_value = [{'login': 'alice'}]
        
        # Desired state: both alice and bob should be in developers team
        desired = {'developers': ['alice', 'bob']}
        
        # Mock the PUT request for adding bob to the team
        self.mock_session.put.return_value.status_code = 200
        
        # Call the function
        invited = yaml_to_github.apply_memberships(
            self.org,
            self.mock_session,
            desired,
            org_members,
            pending_invites,
            existing_slugs
        )
        
        # Verify bob was added to the team (PUT request called)
        self.mock_session.put.assert_called_once()
        call_args = self.mock_session.put.call_args
        self.assertIn('/memberships/bob', call_args[0][0])
        
        # No invites should be sent (bob is already in org)
        self.assertEqual(len(invited), 0)

    @patch('yaml_to_github.paginate')
    @patch('yaml_to_github.invite_by_login')
    def test_adding_non_org_member_to_team(self, mock_invite, mock_paginate):
        """Test adding someone to a team who is not in the org (sends invite)."""
        # Setup: charlie is not in org
        org_members = {'alice', 'bob'}
        pending_invites = set()
        existing_slugs = {'developers'}
        
        # Current team members
        mock_paginate.return_value = [{'login': 'alice'}]
        
        # Desired state: charlie should be added (but needs invite first)
        desired = {'developers': ['alice', 'charlie']}
        
        # Mock invite function to return True (invite sent)
        mock_invite.return_value = True
        
        # Call the function
        invited = yaml_to_github.apply_memberships(
            self.org,
            self.mock_session,
            desired,
            org_members,
            pending_invites,
            existing_slugs
        )
        
        # Verify invite was sent for charlie
        mock_invite.assert_called_once_with(self.org, 'charlie', self.mock_session)
        self.assertIn('charlie', invited)
        
        # Verify charlie was NOT added to team (not in org yet)
        # PUT should not be called for charlie
        for call in self.mock_session.put.call_args_list:
            self.assertNotIn('charlie', str(call))

    @patch('yaml_to_github.paginate')
    def test_removing_member_from_team(self, mock_paginate):
        """Test removing someone from a team."""
        # Setup: both alice and bob are in org and in team
        org_members = {'alice', 'bob'}
        pending_invites = set()
        existing_slugs = {'developers'}
        
        # Current team members: both alice and bob
        mock_paginate.return_value = [{'login': 'alice'}, {'login': 'bob'}]
        
        # Desired state: only alice should be in team (remove bob)
        desired = {'developers': ['alice']}
        
        # Mock the DELETE request for removing bob from the team
        self.mock_session.delete.return_value.status_code = 200
        
        # Call the function
        invited = yaml_to_github.apply_memberships(
            self.org,
            self.mock_session,
            desired,
            org_members,
            pending_invites,
            existing_slugs
        )
        
        # Verify bob was removed from the team (DELETE request called)
        self.mock_session.delete.assert_called_once()
        call_args = self.mock_session.delete.call_args
        self.assertIn('/memberships/bob', call_args[0][0])

    @patch('yaml_to_github.paginate')
    @patch('yaml_to_github.invite_by_login')
    def test_no_duplicate_invites_for_pending_users(self, mock_invite, mock_paginate):
        """Test that users with pending invites don't get invited again."""
        # Setup: charlie has a pending invite
        org_members = {'alice'}
        pending_invites = {'charlie'}
        existing_slugs = {'developers'}
        
        # Current team members
        mock_paginate.return_value = [{'login': 'alice'}]
        
        # Desired state: charlie should be added (but already has invite)
        desired = {'developers': ['alice', 'charlie']}
        
        # Call the function
        invited = yaml_to_github.apply_memberships(
            self.org,
            self.mock_session,
            desired,
            org_members,
            pending_invites,
            existing_slugs
        )
        
        # Verify NO invite was sent (charlie already has pending invite)
        mock_invite.assert_not_called()
        self.assertEqual(len(invited), 0)

    @patch('yaml_to_github.sys.exit')
    @patch('yaml_to_github.paginate')
    def test_fails_for_nonexistent_team(self, mock_paginate, mock_exit):
        """Test that script fails when trying to manage a team that doesn't exist."""
        # Setup: nonexistent team
        org_members = {'alice'}
        pending_invites = set()
        existing_slugs = {'developers'}  # only developers exists
        
        # Desired state: try to manage a nonexistent team
        desired = {'nonexistent-team': ['alice']}
        
        # Call the function - should raise SystemExit
        with self.assertRaises(SystemExit):
            yaml_to_github.apply_memberships(
                self.org,
                self.mock_session,
                desired,
                org_members,
                pending_invites,
                existing_slugs
            )


class TestReconcileTeam(unittest.TestCase):
    """Test the reconcile_team function specifically."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_session = MagicMock()
        self.org = 'test-org'
        self.slug = 'developers'

    def test_add_multiple_members(self):
        """Test adding multiple members to a team."""
        want = {'alice', 'bob', 'charlie'}
        have = set()
        org_members = {'alice', 'bob', 'charlie'}
        
        self.mock_session.put.return_value.status_code = 200
        
        yaml_to_github.reconcile_team(
            self.org, self.mock_session, self.slug, want, have, org_members
        )
        
        # Should add all three members
        self.assertEqual(self.mock_session.put.call_count, 3)

    def test_remove_multiple_members(self):
        """Test removing multiple members from a team."""
        want = set()
        have = {'alice', 'bob', 'charlie'}
        org_members = {'alice', 'bob', 'charlie'}
        
        self.mock_session.delete.return_value.status_code = 200
        
        yaml_to_github.reconcile_team(
            self.org, self.mock_session, self.slug, want, have, org_members
        )
        
        # Should remove all three members
        self.assertEqual(self.mock_session.delete.call_count, 3)

    def test_mixed_add_and_remove(self):
        """Test adding and removing members in the same operation."""
        want = {'alice', 'charlie'}
        have = {'alice', 'bob'}
        org_members = {'alice', 'bob', 'charlie'}
        
        self.mock_session.put.return_value.status_code = 200
        self.mock_session.delete.return_value.status_code = 200
        
        yaml_to_github.reconcile_team(
            self.org, self.mock_session, self.slug, want, have, org_members
        )
        
        # Should add charlie
        self.assertEqual(self.mock_session.put.call_count, 1)
        put_call = self.mock_session.put.call_args[0][0]
        self.assertIn('charlie', put_call)
        
        # Should remove bob
        self.assertEqual(self.mock_session.delete.call_count, 1)
        delete_call = self.mock_session.delete.call_args[0][0]
        self.assertIn('bob', delete_call)


class TestInviteMissingMembers(unittest.TestCase):
    """Test the invite_missing_members function."""

    @patch('yaml_to_github.invite_by_login')
    def test_invite_non_org_members(self, mock_invite):
        """Test inviting users who are not in the org."""
        org = 'test-org'
        session = MagicMock()
        want = {'alice', 'bob', 'charlie'}
        org_members = {'alice'}  # only alice is in org
        pending_invites = set()
        
        mock_invite.return_value = True
        
        invited = yaml_to_github.invite_missing_members(
            org, session, want, org_members, pending_invites
        )
        
        # Should invite bob and charlie
        self.assertEqual(len(invited), 2)
        self.assertIn('bob', invited)
        self.assertIn('charlie', invited)
        self.assertEqual(mock_invite.call_count, 2)

    @patch('yaml_to_github.invite_by_login')
    def test_skip_already_invited(self, mock_invite):
        """Test that users with pending invites are skipped."""
        org = 'test-org'
        session = MagicMock()
        want = {'alice', 'bob', 'charlie'}
        org_members = {'alice'}
        pending_invites = {'bob'}  # bob already has invite
        
        mock_invite.return_value = True
        
        invited = yaml_to_github.invite_missing_members(
            org, session, want, org_members, pending_invites
        )
        
        # Should only invite charlie (bob skipped)
        self.assertEqual(len(invited), 1)
        self.assertIn('charlie', invited)
        self.assertEqual(mock_invite.call_count, 1)


if __name__ == '__main__':
    unittest.main()
