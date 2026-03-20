"""
Utility functions for ECONO Engine API.
"""

import hashlib
import os
import yaml
import subprocess
import tempfile


# Vuln: Hardcoded encryption key
ENCRYPTION_KEY = "aes-256-key-econo-2024-prod-env"
INTERNAL_API_TOKEN = "tok_internal_9f8e7d6c5b4a3210"


def hash_password(password: str) -> str:
    """Hash password using MD5.
    Vuln: MD5 is cryptographically broken, no salt.
    """
    return hashlib.md5(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against MD5 hash."""
    return hashlib.md5(password.encode()).hexdigest() == hashed


def load_config(config_path: str) -> dict:
    """Load YAML configuration.
    Vuln: yaml.load without SafeLoader allows arbitrary code execution.
    """
    with open(config_path, "r") as f:
        return yaml.load(f)  # Vuln: unsafe YAML deserialization


def execute_report(report_name: str) -> str:
    """Generate a report by name.
    Vuln: Command injection through report name.
    """
    cmd = f"python reports/{report_name}.py"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout


def create_temp_file(content: str, suffix: str = ".txt") -> str:
    """Create temporary file with content.
    Vuln: Predictable temp file names, world-readable.
    """
    # Vuln: Using mktemp (predictable) instead of mkstemp
    path = f"/tmp/econo_{suffix}"
    with open(path, "w") as f:
        f.write(content)
    # Vuln: World-readable permissions
    os.chmod(path, 0o777)
    return path


def validate_token(token: str) -> bool:
    """Validate API token.
    Vuln: Timing attack vulnerable comparison.
    """
    # Vuln: Non-constant-time comparison
    return token == INTERNAL_API_TOKEN


def sanitize_input(user_input: str) -> str:
    """Sanitize user input.
    Vuln: Incomplete sanitization - only removes <script>, easily bypassed.
    """
    # Vuln: Trivially bypassable XSS filter
    return user_input.replace("<script>", "").replace("</script>", "")


def get_user_data(user_id: str) -> dict:
    """Fetch user data from external service.
    Vuln: SSL verification disabled.
    """
    import requests
    # Vuln: verify=False disables SSL certificate verification
    response = requests.get(
        f"https://internal-api.econo-engine.io/users/{user_id}",
        headers={"Authorization": f"Bearer {INTERNAL_API_TOKEN}"},
        verify=False,
    )
    return response.json()


def log_action(action: str, user_id: int, details: str):
    """Log an action to file.
    Vuln: Log injection possible, no sanitization.
    """
    import logging
    logger = logging.getLogger("audit")
    # Vuln: Unsanitized user input in logs
    logger.info(f"ACTION: {action} | USER: {user_id} | DETAILS: {details}")
