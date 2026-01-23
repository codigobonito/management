"""Tests for validate_pr.py script."""

import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import os

# Set required environment variables before importing
os.environ['ORG'] = 'test-org'
os.environ['TOKEN'] = 'test-token'

# Add parent directory to path to import the script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import validate_pr


class TestUserExists(unittest.TestCase):
    """Test the user_exists function."""

    @patch('validate_pr.requests.get')
    def test_user_exists_returns_true_for_valid_user(self, mock_get):
        """Test that user_exists returns True for a valid user."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = validate_pr.user_exists('validuser')
        self.assertTrue(result)
        mock_get.assert_called_once()

    @patch('validate_pr.requests.get')
    def test_user_exists_returns_false_for_invalid_user(self, mock_get):
        """Test that user_exists returns False for a non-existent user."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = validate_pr.user_exists('nonexistentuser')
        self.assertFalse(result)

    @patch('validate_pr.requests.get')
    @patch('validate_pr.sys.exit')
    def test_user_exists_exits_on_rate_limit(self, mock_exit, mock_get):
        """Test that user_exists exits on rate limit."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.headers = {'X-RateLimit-Remaining': '0'}
        mock_get.return_value = mock_response

        validate_pr.user_exists('anyuser')
        mock_exit.assert_called_once_with(1)


class TestPaginate(unittest.TestCase):
    """Test the paginate function."""

    @patch('validate_pr.requests.get')
    def test_paginate_single_page(self, mock_get):
        """Test pagination with a single page of results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{'login': 'user1'}, {'login': 'user2'}]
        mock_get.return_value = mock_response

        result = validate_pr.paginate('https://api.github.com/orgs/test/members')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['login'], 'user1')

    @patch('validate_pr.requests.get')
    def test_paginate_multiple_pages(self, mock_get):
        """Test pagination with multiple pages."""
        # First page (100 items)
        page1 = [{'login': f'user{i}'} for i in range(100)]
        # Second page (50 items)
        page2 = [{'login': f'user{i}'} for i in range(100, 150)]

        mock_response1 = MagicMock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = page1

        mock_response2 = MagicMock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = page2

        mock_get.side_effect = [mock_response1, mock_response2]

        result = validate_pr.paginate('https://api.github.com/orgs/test/members')
        self.assertEqual(len(result), 150)


class TestMainValidation(unittest.TestCase):
    """Test the main validation logic."""

    @patch('validate_pr.Path')
    @patch('validate_pr.paginate')
    @patch('validate_pr.user_exists')
    @patch('validate_pr.sys.exit')
    def test_main_exits_on_invalid_user(self, mock_exit, mock_user_exists, mock_paginate, mock_path):
        """Test that main exits when an invalid user is found."""
        # Mock file reading
        mock_path.return_value.read_text.return_value = """
teams:
  admins:
    - validuser
    - invaliduser
"""
        # Mock paginate to return org members
        mock_paginate.return_value = [{'login': 'validuser'}]
        
        # Mock user_exists: first user exists, second doesn't
        mock_user_exists.side_effect = [True, False]

        validate_pr.main()
        mock_exit.assert_called_once_with(1)

    @patch('validate_pr.Path')
    @patch('validate_pr.paginate')
    @patch('validate_pr.user_exists')
    @patch('validate_pr.sys.exit')
    def test_main_succeeds_with_valid_users(self, mock_exit, mock_user_exists, mock_paginate, mock_path):
        """Test that main succeeds when all users are valid."""
        # Mock file reading
        mock_path.return_value.read_text.return_value = """
teams:
  admins:
    - validuser1
    - validuser2
"""
        # Mock paginate to return org members
        mock_paginate.return_value = [{'login': 'validuser1'}, {'login': 'validuser2'}]
        
        # Mock user_exists: both users exist
        mock_user_exists.return_value = True

        validate_pr.main()
        # Should not exit with error
        mock_exit.assert_not_called()


if __name__ == '__main__':
    unittest.main()
