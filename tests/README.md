# Running Tests

This directory contains unit tests for the management scripts.

## Prerequisites

Install pytest (optional but recommended):
```bash
pip install pytest pytest-cov
```

## Running Tests

### Using unittest (built-in)
```bash
# Run all tests
python -m unittest discover tests

# Run a specific test file
python -m unittest tests.test_validate_pr

# Run with verbose output
python -m unittest discover tests -v
```

### Using pytest (recommended)
```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=scripts --cov-report=html

# Run a specific test file
pytest tests/test_validate_pr.py -v
```

## Test Coverage

The test suite covers:
- **validate_pr.py**: User validation, pagination, and main validation logic
- **Retry logic**: Configuration consistency, session creation, and retry behavior
- **yaml_to_github.py**: Team membership synchronization from YAML to GitHub
  - Adding org members to teams
  - Adding non-org members to teams (with invites)
  - Removing members from teams
  - Handling pending invites
- **github_to_yaml.py**: Team membership export from GitHub to YAML
  - Adding members to teams in exports
  - Removing members from teams in exports
  - Removing members from org in exports
  - Preserving pending invites during export
- **Integration**: Ensures retry logic is properly used in both sync scripts

## Writing New Tests

When adding new features:
1. Create tests in the appropriate `test_*.py` file
2. Use mocking to avoid actual API calls
3. Test both success and failure cases
4. Verify error handling and edge cases
