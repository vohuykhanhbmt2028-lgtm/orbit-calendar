#!/usr/bin/env python3
import os
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Get API key
api_key = os.getenv('CLAUDE_API_KEY')
print(f"API Key found: {api_key[:10]}..." if api_key else "API Key NOT found!")

if not api_key:
    print("Error: No API key found!")
    exit(1)

# Initialize client
client = Anthropic(api_key=api_key)

# Test API call
print("\nTesting API connection...")
try:
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=100,
        messages=[
            {"role": "user", "content": "Say hello in one word"}
        ]
    )
    print(f"✅ API working! Response: {message.content[0].text}")
except Exception as e:
    print(f"❌ API Error: {e}")