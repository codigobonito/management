"""Tests for retry logic in sync scripts."""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path to import the scripts
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import github_to_yaml
import yaml_to_github


class TestRetryConfiguration(unittest.TestCase):
    """Test retry configuration constants."""

    def test_retry_constants_match(self):
        """Test that retry constants are consistent across both scripts."""
        self.assertEqual(github_to_yaml.RETRY_TOTAL, yaml_to_github.RETRY_TOTAL)
        self.assertEqual(github_to_yaml.RETRY_BACKOFF_FACTOR, yaml_to_github.RETRY_BACKOFF_FACTOR)
        self.assertEqual(github_to_yaml.RETRY_STATUS_FORCELIST, yaml_to_github.RETRY_STATUS_FORCELIST)

    def test_retry_total_is_positive(self):
        """Test that retry total is a positive number."""
        self.assertGreater(github_to_yaml.RETRY_TOTAL, 0)
        self.assertGreater(yaml_to_github.RETRY_TOTAL, 0)

    def test_retry_status_forcelist_includes_rate_limit(self):
        """Test that retry status forcelist includes 429 (rate limit)."""
        self.assertIn(429, github_to_yaml.RETRY_STATUS_FORCELIST)
        self.assertIn(429, yaml_to_github.RETRY_STATUS_FORCELIST)

    def test_retry_status_forcelist_includes_server_errors(self):
        """Test that retry status forcelist includes 5xx errors."""
        for status in [500, 502, 503, 504]:
            self.assertIn(status, github_to_yaml.RETRY_STATUS_FORCELIST)
            self.assertIn(status, yaml_to_github.RETRY_STATUS_FORCELIST)


class TestCreateSession(unittest.TestCase):
    """Test the create_session function."""

    def test_create_session_returns_session(self):
        """Test that create_session returns a requests.Session object."""
        import requests
        session = github_to_yaml.create_session('test-token')
        self.assertIsInstance(session, requests.Session)

        session = yaml_to_github.create_session('test-token')
        self.assertIsInstance(session, requests.Session)

    def test_create_session_sets_headers(self):
        """Test that create_session sets authorization headers."""
        session = github_to_yaml.create_session('test-token')
        self.assertIn('Authorization', session.headers)
        
        session = yaml_to_github.create_session('test-token')
        self.assertIn('Authorization', session.headers)

    @patch('github_to_yaml.HTTPAdapter')
    @patch('github_to_yaml.Retry')
    def test_create_session_configures_retry(self, mock_retry, mock_adapter):
        """Test that create_session configures retry logic."""
        github_to_yaml.create_session('test-token')
        
        # Verify Retry was called with correct parameters
        mock_retry.assert_called_once_with(
            total=github_to_yaml.RETRY_TOTAL,
            backoff_factor=github_to_yaml.RETRY_BACKOFF_FACTOR,
            status_forcelist=github_to_yaml.RETRY_STATUS_FORCELIST,
            respect_retry_after_header=True
        )
        
        # Verify HTTPAdapter was created with retries
        mock_adapter.assert_called_once()


class TestPaginateWithRetry(unittest.TestCase):
    """Test that paginate function uses session with retry."""

    @patch('github_to_yaml.requests.Session')
    def test_paginate_uses_session_get(self, mock_session_class):
        """Test that paginate uses session.get instead of requests.get."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{'login': 'user1'}]
        mock_session.get.return_value = mock_response
        
        # Call paginate with a session
        result = github_to_yaml.paginate('https://api.github.com/test', mock_session)
        
        # Verify session.get was called
        mock_session.get.assert_called()
        self.assertEqual(len(result), 1)

    @patch('yaml_to_github.requests.Session')
    def test_yaml_to_github_paginate_uses_session(self, mock_session_class):
        """Test that yaml_to_github paginate uses session."""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{'slug': 'team1'}]
        mock_session.get.return_value = mock_response
        
        result = yaml_to_github.paginate('https://api.github.com/test', mock_session)
        
        mock_session.get.assert_called()
        self.assertEqual(len(result), 1)


if __name__ == '__main__':
    unittest.main()
