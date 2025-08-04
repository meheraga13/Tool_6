"""
Configuration settings for the stored procedure transformation validation project.
"""

import os
from pathlib import Path



# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()  # This loads .env file automatically
    print("Loaded .env file")
except ImportError:
    print("python-dotenv not installed. Install with: pip install python-dotenv")
    print("   Using system environment variables instead")

# Project structure
PROJECT_ROOT = Path(__file__).parent
SAMPLES_DIR = PROJECT_ROOT / "samples"
ASTS_DIR = PROJECT_ROOT / "asts"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
REPORTS_DIR = PROJECT_ROOT / "reports"
LINEAGE_DIR = PROJECT_ROOT / "lineage"

# Database configurations
DATABASE_CONFIGS = {
    "sybase": {
        "driver": "FreeTDS",
        "server": "localhost",
        "port": 5000,
        "database": "test_db",
        "username": "sa",
        "password": "password",
        "timeout": 30
    },
    "postgres": {
        "host": "localhost",
        "port": 5432,
        "database": "test_db",
        "username": "postgres",
        "password": "password",
        "timeout": 30
    }
}

# LLM Configuration
LLM_CONFIG = {
    # Try OpenRouter first, then OpenAI
    "api_key": os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", ""),
    "base_url": os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/deepseek/deepseek-chat-v3-0324:free"),  # Default to OpenAI, or use OpenRouter
    "model": os.getenv("OPENROUTER_MODEL", "mistralai/codestral-2508"),
    "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.3")),
    "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "2000"))
}

# AST Schema validation
AST_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "ast_schema.json"

# Comparison thresholds
COMPARISON_THRESHOLDS = {
    "similarity_threshold": 0.85,
    "critical_diff_threshold": 0.7,
    "warning_diff_threshold": 0.5
}

# Test execution settings
TEST_EXECUTION = {
    "timeout": 300,  # 5 minutes
    "max_retries": 3,
    "parallel_execution": True,
    "max_workers": 4
}

# Report settings
REPORT_CONFIG = {
    "output_format": "markdown",
    "include_detailed_diff": True,
    "include_lineage_analysis": True,
    "include_performance_metrics": True
}

# Logging configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "filename": str(PROJECT_ROOT / "logs" / "validation.log")
}

# ANTLR configuration
ANTLR_CONFIG = {
    "postgres_grammar": "PostgreSQL",
    "sybase_grammar": "TSql",
    "parser_timeout": 30,
    "error_strategy": "DefaultErrorStrategy"
}

# Validation rules
VALIDATION_RULES = {
    "required_procedures": [],
    "forbidden_constructs": ["GOTO", "RAISERROR"],
    "naming_conventions": {
        "procedures": r"^[a-zA-Z][a-zA-Z0-9_]*$",
        "variables": r"^[a-zA-Z][a-zA-Z0-9_]*$",
        "parameters": r"^[a-zA-Z][a-zA-Z0-9_]*$"
    }
}