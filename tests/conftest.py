"""
Shared pytest setup for the whole test suite.

pytest imports this file before collecting any test module, and config.py builds its
settings at import time, so the credentials below are in place before the first
`import config`. They are assigned directly (not setdefault) so a real token from the
shell or a local .env can never reach a test: load_dotenv() does not override variables
that are already set, and pydantic-settings prefers environment variables over .env.
"""

import os

os.environ["TODOIST_API_TOKEN"] = "test-todoist-token-not-real"
os.environ["WEBHOOK_SECRET_TOKEN"] = "test-webhook-secret-not-real"
