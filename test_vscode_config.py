#!/usr/bin/env python3
"""
Test script to verify VSCode configuration
"""
import os
import sys

print("=== VSCode Configuration Test ===")
print(f"Python executable: {sys.executable}")
print(f"Python path: {sys.path}")
print(f"Current working directory: {os.getcwd()}")
print(f"PYTHONPATH environment variable: {os.environ.get('PYTHONPATH', 'Not set')}")

# Try to import the src module
try:
    import src.configs.config
    print("✅ SUCCESS: src module imported successfully!")
    print("VSCode configuration is working correctly.")
except ImportError as e:
    print(f"❌ FAILED: {e}")
    print("VSCode configuration needs adjustment.")
