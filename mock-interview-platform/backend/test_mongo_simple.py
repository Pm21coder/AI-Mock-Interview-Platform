#!/usr/bin/env python3
"""Direct MongoDB connection test."""

import os
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, OperationFailure
from dotenv import load_dotenv
import ssl

load_dotenv()
mongo_uri = os.getenv("MONGODB_URI")

print("Testing MongoDB connection...")
print(f"URI: {mongo_uri[:80]}...\n")

try:
    print("[1] Connecting with default settings...")
    client = MongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
        socketTimeoutMS=10000
    )
    print("    Attempting to ping...")
    result = client.admin.command('ping')
    print(f"    ✅ SUCCESS! Ping response: {result}")
    client.close()
    
except ServerSelectionTimeoutError as e:
    print(f"    ❌ Timeout: {str(e)[:150]}\n")
    
except OperationFailure as e:
    print(f"    ❌ Operation failed: {str(e)[:150]}\n")
    
except Exception as e:
    import traceback
    error_type = type(e).__name__
    error_msg = str(e)
    print(f"    ❌ {error_type}")
    print(f"    Message: {error_msg[:200]}\n")
    print("Full traceback:")
    traceback.print_exc()
    
    # Diagnostics
    if "TLSV1_ALERT" in error_msg or "SSL" in error_msg or "TLS" in error_msg:
        print("\n⚠️  TLS/SSL ERROR DETECTED")
        print("Trying with cert verification disabled (diagnostic only)...")
        try:
            client = MongoClient(
                mongo_uri,
                tls=True,
                tlsAllowInvalidCertificates=True,
                serverSelectionTimeoutMS=5000
            )
            result = client.admin.command('ping')
            print(f"✅ Works with tlsAllowInvalidCertificates=True")
            print(f"   → Issue is cert validation (missing/outdated CA bundle)")
            print(f"   → Fix: pip install --upgrade certifi")
            client.close()
        except Exception as e2:
            print(f"❌ Still fails: {type(e2).__name__}: {str(e2)[:100]}")
