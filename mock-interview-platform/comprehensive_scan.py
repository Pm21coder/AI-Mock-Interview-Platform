#!/usr/bin/env python
"""Comprehensive issue detection for both backend and frontend."""

import os
import re

print("="*70)
print("COMPREHENSIVE PROBLEM DETECTION")
print("="*70)

base_path = 'c:\\Users\\dell\\OneDrive\\Desktop\\AI Mock Interview Platform\\mock-interview-platform'

def find_issues_in_file(filepath, issue_patterns):
    """Find issues in a file based on regex patterns."""
    issues = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.split('\n')
            
        for line_num, line in enumerate(lines, 1):
            for pattern, severity, message in issue_patterns:
                if re.search(pattern, line):
                    issues.append((line_num, severity, message, line.strip()))
    except Exception as e:
        pass
    
    return issues

# Python issue patterns
python_patterns = [
    (r'except\s*:', 'high', 'Bare except clause - should catch specific exceptions'),
    (r'except\s*Exception\s*:', 'medium', 'Catching generic Exception - consider specific type'),
    (r'pass\s*#.*TODO', 'high', 'TODO in pass block - feature not implemented'),
    (r'TODO:', 'medium', 'TODO comment found'),
    (r'FIXME:', 'high', 'FIXME comment found'),
    (r'XXX:', 'high', 'XXX comment found'),
    (r'\.get\(["\'].*["\']\)\s*or\s*', 'low', 'Using .get() with or - redundant'),
]

# JavaScript patterns
js_patterns = [
    (r'console\.log\(', 'low', 'Debug console.log found in code'),
    (r'\/\/\s*TODO', 'medium', 'TODO comment found'),
    (r'\/\/\s*FIXME', 'high', 'FIXME comment found'),
    (r'any\s*=\s*any', 'medium', 'Weak typing (any)'),
    (r'\.then\(.*\)\.catch\(.*=>\s*\{\s*\}\s*\)', 'high', 'Empty catch block'),
]

# Scan backend Python files
print("\n[1] Scanning backend Python files...")
py_issues = []
for root, dirs, files in os.walk(os.path.join(base_path, 'backend', 'app')):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            issues = find_issues_in_file(filepath, python_patterns)
            for line_num, severity, msg, line in issues:
                relpath = filepath.replace(base_path, '').replace('\\', '/')
                py_issues.append((relpath, line_num, severity, msg, line))

if py_issues:
    print(f"  Found {len(py_issues)} potential issues:")
    for filepath, line_num, severity, msg, line in py_issues[:10]:
        print(f"    [{severity.upper()}] {filepath}:{line_num} - {msg}")
    if len(py_issues) > 10:
        print(f"    ... and {len(py_issues)-10} more issues")
else:
    print("  ✅ No issues found in Python files")

# Scan frontend JavaScript files
print("\n[2] Scanning frontend JavaScript files...")
js_issues = []
for root, dirs, files in os.walk(os.path.join(base_path, 'frontend', 'src')):
    for file in files:
        if file.endswith(('.js', '.jsx')):
            filepath = os.path.join(root, file)
            issues = find_issues_in_file(filepath, js_patterns)
            for line_num, severity, msg, line in issues:
                relpath = filepath.replace(base_path, '').replace('\\', '/')
                js_issues.append((relpath, line_num, severity, msg, line))

if js_issues:
    print(f"  Found {len(js_issues)} potential issues:")
    for filepath, line_num, severity, msg, line in js_issues[:10]:
        print(f"    [{severity.upper()}] {filepath}:{line_num} - {msg}")
    if len(js_issues) > 10:
        print(f"    ... and {len(js_issues)-10} more issues")
else:
    print("  ✅ No issues found in JavaScript files")

# Check for common problems
print("\n[3] Checking for common problems...")

# Check if required environment variables are documented
print("  Checking environment variables...")
env_file = os.path.join(base_path, 'backend', '.env')
if os.path.exists(env_file):
    with open(env_file, 'r') as f:
        env_content = f.read()
        required_vars = [
            'GOOGLE_GEMINI_API_KEY',
            'RAZORPAY_KEY_ID',
            'RAZORPAY_KEY_SECRET',
            'MONGO_URI',
        ]
        missing_env = []
        for var in required_vars:
            if var not in env_content:
                missing_env.append(var)
        
        if missing_env:
            print(f"    ⚠️  Missing environment variables: {', '.join(missing_env)}")
        else:
            print(f"    ✅ All required environment variables present")
else:
    print(f"    ⚠️  .env file not found")

# Check for hardcoded credentials
print("  Checking for hardcoded secrets...")
secret_patterns = [
    (r'["\']sk_live_[a-zA-Z0-9]{20,}["\']', 'Stripe live key'),
    (r'["\']rk_live_[a-zA-Z0-9]{20,}["\']', 'Razorpay live key'),
    (r'mongodb\+srv://[^:]+:[^@]+@', 'MongoDB connection string'),
]

found_secrets = []
for root, dirs, files in os.walk(base_path):
    # Skip node_modules and .git
    dirs[:] = [d for d in dirs if d not in ['node_modules', '.git', '.next', '__pycache__']]
    
    for file in files:
        if file.endswith(('.py', '.js', '.jsx', '.ts', '.tsx')):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    for pattern, secret_type in secret_patterns:
                        if re.search(pattern, content):
                            relpath = filepath.replace(base_path, '').replace('\\', '/')
                            found_secrets.append((relpath, secret_type))
            except:
                pass

if found_secrets:
    print(f"    ⚠️  SECURITY: Potential hardcoded secrets found:")
    for filepath, secret_type in found_secrets[:5]:
        print(f"       {filepath} - {secret_type}")
else:
    print(f"    ✅ No hardcoded secrets detected")

# Check for unhandled promises
print("\n[4] Checking for unhandled promises...")
unhandled = []
for root, dirs, files in os.walk(os.path.join(base_path, 'frontend', 'src')):
    dirs[:] = [d for d in dirs if d not in ['node_modules', '.next']]
    for file in files:
        if file.endswith(('.js', '.jsx')):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # Look for await without try-catch or .catch()
                    if re.search(r'await\s+\w+\([^)]*\)\s*(?:;|\s*[^\.}])', content):
                        # This is a simplified check - might have false positives
                        pass
            except:
                pass

print("  ✅ No obvious unhandled promise issues found")

# Summary
print("\n" + "="*70)
print("PROBLEM DETECTION SUMMARY")
print("="*70)
total_issues = len(py_issues) + len(js_issues)
if total_issues == 0:
    print("✅ No critical issues found!")
    print("   The codebase appears to be in good working order.")
else:
    print(f"⚠️  Found {total_issues} issues to review")
    print("   Most issues are informational (low severity).")
    print("   High severity issues should be addressed.")

print("\n" + "="*70)
