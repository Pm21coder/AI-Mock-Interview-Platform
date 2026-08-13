#!/usr/bin/env python3
"""Test TLS handshake with cert verification disabled."""

import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
mongo_uri = os.getenv("MONGODB_URI")

print("Testing with tlsAllowInvalidCertificates=True (diagnostic)...")

try:
    client = MongoClient(
        mongo_uri,
        tls=True,
        tlsAllowInvalidCertificates=True,
        serverSelectionTimeoutMS=10000
    )
    result = client.admin.command('ping')
    print(f"✅ SUCCESS with tlsAllowInvalidCertificates=True!")
    print(f"   Response: {result}")
    print(f"\n   This indicates a certificate validation issue.")
    print(f"   The CA bundle or cert path may be misconfigured.")
    client.close()
except Exception as e:
    print(f"❌ Still fails: {type(e).__name__}")
    print(f"   {str(e)[:200]}")
    print(f"\n   This indicates a deeper TLS/cipher issue, not cert validation.")
