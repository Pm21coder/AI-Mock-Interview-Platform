#!/usr/bin/env python3
"""Diagnostic script for MongoDB Atlas TLS handshake issues."""

import ssl
import socket
import os
import sys
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, OperationFailure
from urllib.parse import urlparse
import certifi

print("=" * 70)
print("MongoDB Atlas TLS Handshake Diagnostic")
print("=" * 70)

# 1. Show environment
print("\n[1] Environment & Versions")
print(f"  Python: {sys.version.split()[0]}")
print(f"  OpenSSL: {ssl.OPENSSL_VERSION}")
print(f"  PyMongo: ", end="")
import pymongo
print(pymongo.__version__)
print(f"  Certifi: {certifi.where()}")

# 2. Check MongoDB URI
from dotenv import load_dotenv
load_dotenv()
mongo_uri = os.getenv("MONGODB_URI")
if not mongo_uri:
    print("\n❌ ERROR: MONGODB_URI not set in .env")
    sys.exit(1)

print(f"\n[2] MongoDB URI Configuration")
parsed = urlparse(mongo_uri)
print(f"  Host: {parsed.hostname}")
print(f"  Database: {parsed.path.split('/')[-1]}")
print(f"  TLS/SSL: Enabled (mongodb+srv://)")
print(f"  Full URI: {mongo_uri[:80]}..." if len(mongo_uri) > 80 else f"  Full URI: {mongo_uri}")

# 3. Try DNS resolution
print(f"\n[3] DNS Resolution Test")
try:
    hostname = parsed.hostname
    ip = socket.gethostbyname(hostname)
    print(f"  ✅ {hostname} → {ip}")
except socket.gaierror as e:
    print(f"  ❌ DNS resolution failed: {e}")
    sys.exit(1)

# 4. Try basic socket connection (no TLS)
print(f"\n[4] Basic TCP Connection Test")
try:
    sock = socket.create_connection((hostname, 27017), timeout=5)
    sock.close()
    print(f"  ✅ TCP connection to {hostname}:27017 succeeded")
except Exception as e:
    print(f"  ⚠️  TCP connection failed: {e}")
    print(f"      (This is OK for MongoDB Atlas SRV records)")

# 5. Try TLS connection with different options
print(f"\n[5] TLS Connection Tests")

configs = [
    {
        "name": "Default (with TLS verification)",
        "kwargs": {"serverSelectionTimeoutMS": 5000}
    },
    {
        "name": "Force TLS explicitly",
        "kwargs": {"tls": True, "serverSelectionTimeoutMS": 5000}
    },
    {
        "name": "Skip cert verification (diagnostic only)",
        "kwargs": {"tls": True, "tlsAllowInvalidCertificates": True, "serverSelectionTimeoutMS": 5000}
    },
    {
        "name": "With explicit CA bundle",
        "kwargs": {"tls": True, "tlsCAFile": certifi.where(), "serverSelectionTimeoutMS": 5000}
    }
]

for i, config in enumerate(configs, 1):
    print(f"\n  Test {i}: {config['name']}")
    try:
        client = MongoClient(mongo_uri, **config['kwargs'])
        # Try to ping
        result = client.admin.command('ping')
        print(f"    ✅ Connection successful! Ping response: {result}")
        client.close()
    except ServerSelectionTimeoutError as e:
        print(f"    ❌ Timeout: {str(e)[:100]}")
    except OperationFailure as e:
        print(f"    ❌ Operation failed: {str(e)[:100]}")
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)[:100]
        print(f"    ❌ {error_type}: {error_msg}")
        
        # Special handling for TLS errors
        if "TLSV1_ALERT" in error_msg or "SSL" in error_msg or "TLS" in error_msg:
            print(f"       → This looks like a TLS/SSL issue")
            if "INTERNAL_ERROR" in error_msg:
                print(f"       → Suggests cert validation or version mismatch")

print("\n" + "=" * 70)
print("Diagnosis complete. Check results above.")
print("=" * 70)
