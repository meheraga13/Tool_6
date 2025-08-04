#!/usr/bin/env python3
"""
Debug script to test the TestScriptGenerator directly and identify issues.
"""

import sys
from pathlib import Path
import traceback

project_root = Path(__file__).parent
scripts_path = project_root / "scripts"

sys.path.insert(0, str(scripts_path))


def test_imports():
    """Test all imports to identify missing dependencies."""
    print("Testing imports...")
    
    try:
        import json
        print("✅ json imported successfully")
    except ImportError as e:
        print(f"❌ json import failed: {e}")
        return False
    
    try:
        import logging
        print("✅ logging imported successfully")
    except ImportError as e:
        print(f"❌ logging import failed: {e}")
        return False
    
    try:
        from pathlib import Path
        print("✅ pathlib imported successfully")
    except ImportError as e:
        print(f"❌ pathlib import failed: {e}")
        return False
    
    try:
        from typing import Any, Dict, List, Optional, Tuple
        print("✅ typing imported successfully")
    except ImportError as e:
        print(f"❌ typing import failed: {e}")
        return False
    
    try:
        import openai
        print("✅ openai imported successfully")
    except ImportError as e:
        print(f"❌ openai import failed: {e}")
        print("   Install with: pip install openai")
        return False
    
    try:
        from jinja2 import Template
        print("✅ jinja2 imported successfully")
    except ImportError as e:
        print(f"❌ jinja2 import failed: {e}")
        print("   Install with: pip install jinja2")
        return False
    
    try:
        from config import LLM_CONFIG, LOGGING_CONFIG, PROJECT_ROOT, ASTS_DIR, REPORTS_DIR

        print("✅ config imported successfully")
    except ImportError as e:
        print(f"❌ config import failed: {e}")
        print("   Make sure config.py exists and is properly configured")
        return False
    
    return True


def test_config():
    """Test configuration values."""
    print("\nTesting configuration...")
    
    try:
        from config import LLM_CONFIG, LOGGING_CONFIG, PROJECT_ROOT, ASTS_DIR, REPORTS_DIR
        
        print(f"✅ PROJECT_ROOT: {PROJECT_ROOT}")
        print(f"✅ ASTS_DIR: {ASTS_DIR}")
        print(f"✅ REPORTS_DIR: {REPORTS_DIR}")
        
        # Check LLM_CONFIG
        required_keys = ["api_key", "model", "temperature", "max_tokens"]
        for key in required_keys:
            if key in LLM_CONFIG:
                if key == "api_key":
                    print(f"✅ LLM_CONFIG['{key}']: {'Set' if LLM_CONFIG[key] else 'Not Set'}")
                else:
                    print(f"✅ LLM_CONFIG['{key}']: {LLM_CONFIG[key]}")
            else:
                print(f"❌ LLM_CONFIG['{key}']: Missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False


def test_openai_connection():
    """Test OpenAI/OpenRouter connection."""
    print("\nTesting LLM connection...")
    
    try:
        from config import LLM_CONFIG
        import openai
        
        client = openai.OpenAI(
            api_key=LLM_CONFIG["api_key"],
            base_url=LLM_CONFIG.get("base_url", "https://api.openai.com/v1")
        )
        
        # Try a simple completion
        response = client.chat.completions.create(
            model=LLM_CONFIG["model"],
            messages=[
                {"role": "user", "content": "Say 'connection test successful'"}
            ],
            max_tokens=10,
            temperature=0
        )
        
        print("✅ LLM connection successful")
        print(f"   Response: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ LLM connection failed: {e}")
        return False


def test_directories():
    """Test directory structure and permissions."""
    print("\nTesting directories...")
    
    try:
        from config import PROJECT_ROOT, ASTS_DIR, REPORTS_DIR
        
        # Check PROJECT_ROOT
        if PROJECT_ROOT.exists():
            print(f"✅ PROJECT_ROOT exists: {PROJECT_ROOT}")
        else:
            print(f"❌ PROJECT_ROOT does not exist: {PROJECT_ROOT}")
            return False
        
        # Check ASTS_DIR
        if ASTS_DIR.exists():
            print(f"✅ ASTS_DIR exists: {ASTS_DIR}")
        else:
            print(f"⚠️  ASTS_DIR does not exist: {ASTS_DIR}")
            print("   This is expected if no AST files have been generated yet")
        
        # Check REPORTS_DIR
        if REPORTS_DIR.exists():
            print(f"✅ REPORTS_DIR exists: {REPORTS_DIR}")
        else:
            print(f"⚠️  REPORTS_DIR does not exist: {REPORTS_DIR}")
            print("   Will be created automatically")
        
        # Test write permissions
        test_dir = PROJECT_ROOT / "tests"
        try:
            test_dir.mkdir(exist_ok=True)
            test_file = test_dir / "write_test.tmp"
            test_file.write_text("test")
            test_file.unlink()
            print("✅ Write permissions OK")
        except Exception as e:
            print(f"❌ Write permission test failed: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Directory test failed: {e}")
        return False


def test_test_script_generator():
    """Test TestScriptGenerator initialization."""
    print("\nTesting TestScriptGenerator...")
    
    try:
        # Import the class
        sys.path.append(str(Path(__file__).parent))
        
        # Create a minimal version to test initialization
        from config import LLM_CONFIG
        import openai
        from jinja2 import Template
        
        # Test OpenAI client creation
        client = openai.OpenAI(
            api_key=LLM_CONFIG["api_key"],
            base_url=LLM_CONFIG.get("base_url", "https://api.openai.com/v1")
        )
        print("✅ OpenAI client created successfully")
        
        # Test template creation
        test_template = Template("Test template: {{ test_var }}")
        result = test_template.render(test_var="success")
        print(f"✅ Jinja2 template test: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ TestScriptGenerator test failed: {e}")
        traceback.print_exc()
        return False


def create_sample_ast_files():
    """Create sample AST files for testing."""
    print("\nCreating sample AST files...")
    
    try:
        from config import ASTS_DIR
        import json
        
        # Ensure ASTS_DIR exists
        ASTS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Sample Sybase AST
        sybase_ast = [{
            "proc_name": "test_procedure",
            "params": [
                {"name": "input_id", "type": "INTEGER", "mode": "IN"},
                {"name": "result_msg", "type": "VARCHAR(255)", "mode": "OUT"}
            ],
            "return_type": "INTEGER",
            "variables": [
                {"name": "local_var", "type": "INTEGER"}
            ],
            "statements": [
                {
                    "type": "SET",
                    "name": "local_var",
                    "value": "input_id * 2"
                },
                {
                    "type": "IF",
                    "condition": "local_var > 0",
                    "then": [
                        {
                            "type": "SET",
                            "name": "result_msg",
                            "value": "'Success'"
                        }
                    ],
                    "else": [
                        {
                            "type": "SET",
                            "name": "result_msg",
                            "value": "'Failed'"
                        }
                    ]
                },
                {
                    "type": "RETURN",
                    "expression": "0"
                }
            ]
        }]
        
        # Save Sybase AST
        sybase_file = ASTS_DIR / "sybase_ast.json"
        with open(sybase_file, 'w') as f:
            json.dump(sybase_ast, f, indent=2)
        print(f"✅ Created sample Sybase AST: {sybase_file}")
        
        # Save PostgreSQL AST (same for testing)
        postgres_file = ASTS_DIR / "postgres_ast.json"
        with open(postgres_file, 'w') as f:
            json.dump(sybase_ast, f, indent=2)
        print(f"✅ Created sample PostgreSQL AST: {postgres_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create sample AST files: {e}")
        traceback.print_exc()
        return False


def run_test_generation():
    """Run the actual test generation."""
    print("\nRunning test generation...")
    
    try:
        # Import and run the test generator
        from generate_test_sql import TestScriptGenerator, load_ast_files
        
        # Load AST files
        sybase_ast, postgres_ast = load_ast_files()
        print(f"✅ Loaded {len(sybase_ast)} Sybase procedures")
        print(f"✅ Loaded {len(postgres_ast)} PostgreSQL procedures")
        
        # Create generator
        generator = TestScriptGenerator()
        print("✅ TestScriptGenerator created successfully")
        
        # Generate test scripts
        print("🔄 Generating test scripts...")
        results = generator.generate_test_scripts(sybase_ast, postgres_ast)
        print("✅ Test scripts generated successfully")
        
        # Save test scripts
        print("🔄 Saving test scripts...")
        saved_files = generator.save_test_scripts(results)
        print("✅ Test scripts saved successfully")
        
        # Print summary
        print(f"\n📊 GENERATION SUMMARY:")
        print(f"   Procedures: {results['generation_summary']['total_procedures']}")
        print(f"   Tests Generated: {results['generation_summary']['tests_generated']}")
        print(f"   Sybase Files: {len(saved_files['sybase_files'])}")
        print(f"   PostgreSQL Files: {len(saved_files['postgres_files'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test generation failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all diagnostic tests."""
    print("🔍 DIAGNOSTIC TEST SCRIPT FOR TEST GENERATOR")
    print("=" * 60)
    
    tests = [
        ("Import Test", test_imports),
        ("Configuration Test", test_config),
        ("LLM Connection Test", test_openai_connection),
        ("Directory Test", test_directories),
        ("TestScriptGenerator Test", test_test_script_generator),
        ("Sample AST Creation", create_sample_ast_files),
        ("Test Generation", run_test_generation)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            traceback.print_exc()
            results[test_name] = False
        
        if not results[test_name]:
            print(f"\n⚠️  {test_name} failed - stopping here")
            break
    
    # Summary
    print(f"\n{'='*60}")
    print("🔍 DIAGNOSTIC SUMMARY")
    print(f"{'='*60}")
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 All tests passed! The test generator should work now.")
    else:
        print("\n⚠️  Some tests failed. Please address the issues above.")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())