#!/usr/bin/env python3
"""
Setup script for Jira integration validation
"""

import os
import base64
import sys
from pathlib import Path

def load_env_file(env_path=".env"):
    """Load environment variables from .env file"""
    env_vars = {}
    try:
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
        return env_vars
    except FileNotFoundError:
        print(f"Environment file {env_path} not found")
        return {}

def validate_credentials():
    """Validate Jira credentials and setup"""
    print("🔍 Validating Jira Integration Setup...")
    
    # Load jira.env file
    jira_env = load_env_file("jira.env")
    
    required_vars = ['JIRA_EMAIL', 'JIRA_SITE', 'JIRA_API_TOKEN', 'JIRA_AUTH_TOKEN_BASE64']
    missing_vars = []
    
    for var in required_vars:
        if var not in jira_env or not jira_env[var] or jira_env[var].startswith('YOUR_'):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing or placeholder values for:")
        for var in missing_vars:
            print(f"   - {var}")
        return False
    
    print("✅ All required variables are set")
    
    # Validate Base64 encoding
    return verify_base64_encoding(jira_env)

def verify_base64_encoding(jira_env):
    """Verify that the Base64 encoding is correct"""
    email = jira_env['JIRA_EMAIL']
    api_token = jira_env['JIRA_API_TOKEN']
    provided_base64 = jira_env['JIRA_AUTH_TOKEN_BASE64']
    
    # Generate expected Base64
    auth_string = f"{email}:{api_token}"
    expected_base64 = base64.b64encode(auth_string.encode()).decode()
    
    if provided_base64 == expected_base64:
        print("✅ Base64 encoding is correct")
        return True
    else:
        print("❌ Base64 encoding mismatch")
        print(f"Expected: {expected_base64}")
        print(f"Provided: {provided_base64}")
        print(f"\n💡 To fix this, run:")
        print(f'echo -n "{auth_string}" | base64')
        return False

def show_github_secrets_setup():
    """Show instructions for setting up GitHub secrets"""
    print("\n🔧 GitHub Secrets Setup Required:")
    print("Add these secrets to your GitHub repository:")
    print("(Go to Settings > Secrets and variables > Actions)")
    print()
    
    jira_env = load_env_file("jira.env")
    
    secrets = [
        ('JIRA_USER_EMAIL', jira_env.get('JIRA_EMAIL', 'YOUR_EMAIL@DOMAIN.COM')),
        ('JIRA_API_TOKEN', jira_env.get('JIRA_API_TOKEN', 'YOUR_JIRA_API_TOKEN_HERE')),
        ('JIRA_AUTH_TOKEN_BASE64', jira_env.get('JIRA_AUTH_TOKEN_BASE64', 'YOUR_BASE64_ENCODED_TOKEN_HERE')),
        ('JIRA_BASE_URL', jira_env.get('JIRA_SITE', 'https://hodgedomain.atlassian.net'))
    ]
    
    for name, value in secrets:
        status = "✅" if not value.startswith('YOUR_') else "❌"
        print(f"{status} {name}: {value}")

if __name__ == "__main__":
    print("=" * 50)
    print("Jira Integration Setup Validator")
    print("=" * 50)
    
    if validate_credentials():
        print("\n🎉 Setup validation successful!")
        show_github_secrets_setup()
    else:
        print("\n❌ Setup validation failed!")
        print("Please check your jira.env file and try again.")
        sys.exit(1)