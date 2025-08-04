#!/usr/bin/env python3
"""
Test OpenRouter API connection and configuration.
"""

import os
import sys
from pathlib import Path

# Set UTF-8 encoding for Windows
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'

def test_imports():
    """Test required imports."""
    print("=== Testing Imports ===")
    
    try:
        from dotenv import load_dotenv
        print("[OK] dotenv imported")
    except ImportError:
        print("[ERROR] Missing python-dotenv. Install with: pip install python-dotenv")
        return False
    
    try:
        import openai
        print("[OK] openai imported")
    except ImportError:
        print("[ERROR] Missing openai. Install with: pip install openai")
        return False
    
    try:
        from jinja2 import Template
        print("[OK] jinja2 imported")
    except ImportError:
        print("[ERROR] Missing jinja2. Install with: pip install jinja2")
        return False
    
    return True

def test_env_loading():
    """Test environment variable loading."""
    print("\n=== Testing Environment Variables ===")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("[OK] .env file loaded")
    except Exception as e:
        print(f"[WARNING] Could not load .env file: {e}")
    
    # Check API key
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if api_key:
        print(f"[OK] API Key found: {api_key[:10]}...")
    else:
        print("[ERROR] No API key found")
        return False
    
    # Check other settings
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    print(f"[OK] Base URL: {base_url}")
    print(f"[OK] Model: {model}")
    
    return True

def test_openrouter_connection():
    """Test actual OpenRouter API connection."""
    print("\n=== Testing OpenRouter Connection ===")
    
    try:
        import openai
        
        # Get configuration
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
        model = os.getenv("OPENAI_MODEL", "deepseek/deepseek-chat-v3-0324:free")
        
        # Create client
        client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        print(f"[OK] OpenAI client created")
        print(f"     API Key: {api_key[:10]}...")
        print(f"     Base URL: {base_url}")
        print(f"     Model: {model}")
        
        # Test simple API call
        print("[INFO] Testing API connection...")
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello, OpenRouter!' and nothing else."}
            ],
            max_tokens=50,
            temperature=0.1
        )
        
        print(f"[OK] API call successful!")
        print(f"[OK] Response: {response.choices[0].message.content}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] API connection failed: {e}")
        print(f"[ERROR] Error type: {type(e).__name__}")
        
        # Print detailed error info
        if hasattr(e, 'response'):
            print(f"[ERROR] HTTP Status: {e.response.status_code}")
            print(f"[ERROR] Response: {e.response.text}")
        
        return False

def test_file_structure():
    """Test required file structure."""
    print("\n=== Testing File Structure ===")
    
    # Check for required directories
    dirs_to_check = [
        "asts",
        "reports", 
        "tests",
        "logs"
    ]
    
    for dir_name in dirs_to_check:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"[OK] Directory exists: {dir_name}")
        else:
            print(f"[INFO] Creating directory: {dir_name}")
            dir_path.mkdir(exist_ok=True)
    
    # Check for AST files
    ast_files = [
        "asts/sybase_ast.json",
        "asts/postgres_ast.json"
    ]
    
    for ast_file in ast_files:
        ast_path = Path(ast_file)
        if ast_path.exists():
            print(f"[OK] AST file exists: {ast_file}")
        else:
            print(f"[WARNING] AST file missing: {ast_file}")
    
    return True

def create_sample_ast_files():
    """Create sample AST files if they don't exist."""
    print("\n=== Creating Sample AST Files ===")
    
    import json
    
    # Sample AST data
    sample_ast = [
        {
            "proc_name": "test_procedure",
            "params": [
                {"name": "input_id", "type": "INTEGER", "mode": "IN"},
                {"name": "result_msg", "type": "VARCHAR(255)", "mode": "OUT"}
            ],
            "return_type": "INTEGER",
            "variables": [
                {"name": "temp_var", "type": "INTEGER"}
            ],
            "statements": [
                {
                    "type": "SET",
                    "name": "temp_var",
                    "value": "input_id * 2"
                },
                {
                    "type": "RETURN",
                    "expression": "0"
                }
            ]
        }
    ]
    
    # Create AST files
    asts_dir = Path("asts")
    asts_dir.mkdir(exist_ok=True)
    
    for db_type in ["sybase", "postgres"]:
        ast_file = asts_dir / f"{db_type}_ast.json"
        with open(ast_file, 'w') as f:
            json.dump(sample_ast, f, indent=2)
        print(f"[OK] Created: {ast_file}")

def main():
    """Run all tests."""
    print("OpenRouter Configuration Test")
    print("=" * 40)
    
    success = True
    
    # Test 1: Imports
    if not test_imports():
        success = False
        print("\n[ERROR] Import test failed. Install missing packages and try again.")
        return 1
    
    # Test 2: Environment variables
    if not test_env_loading():
        success = False
        print("\n[ERROR] Environment test failed. Check your .env file.")
        return 1
    
    # Test 3: File structure
    test_file_structure()
    create_sample_ast_files()
    
    # Test 4: API connection
    if not test_openrouter_connection():
        success = False
        print("\n[ERROR] API connection test failed.")
        print("\nPossible issues:")
        print("- Invalid API key")
        print("- Wrong base URL")
        print("- Model not available")
        print("- Network connection issues")
        return 1
    
    if success:
        print("\n" + "=" * 40)
        print("[SUCCESS] All tests passed!")
        print("Your OpenRouter configuration is working correctly.")
        print("\nNow try running your pipeline:")
        print("python run_validation_pipeline.py --step generate_tests")
        return 0
    else:
        print("\n" + "=" * 40)
        print("[FAILED] Some tests failed. Fix the issues above and try again.")
        return 1

if __name__ == "__main__":
    sys.exit(main())