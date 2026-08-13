#!/usr/bin/env python3
"""Check available Gemini models"""

import sys
from pathlib import Path

backend_path = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_path))

from app.config import Config

try:
    import google.genai as genai
    from google.genai import types
    
    client = genai.Client(api_key=Config.GOOGLE_GEMINI_API_KEY)
    
    print("Available Gemini Models:")
    print("-" * 80)
    
    # List models
    response = client.models.list()
    
    # The response is a pager, iterate through it
    for model in response:
        model_name = model.name if hasattr(model, 'name') else str(model)
        display_name = model.display_name if hasattr(model, 'display_name') else ''
        print(f"  {model_name} ({display_name})")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
