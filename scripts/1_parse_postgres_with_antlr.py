#!/usr/bin/env python3
import json
import logging
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))  # To access parsers package and config

from config import ASTS_DIR, SAMPLES_DIR, LOGGING_CONFIG
from parsers import get_parser_for_dialect

logging.basicConfig(**LOGGING_CONFIG)
logger = logging.getLogger(__name__)

def main():
    postgres_file = SAMPLES_DIR / "postgres_proc.sql"
    if not postgres_file.exists():
        logger.error(f"PostgreSQL sample file doesn't exist: {postgres_file}")
        return 1

    logger.info(f"Reading sample from {postgres_file}")
    with open(postgres_file, "r", encoding="utf-8") as f:
        sql_content = f.read()

    try:
        parser = get_parser_for_dialect("postgresql")
        ast = parser.parse(sql_content)
    except Exception as e:
        logger.error(f"Error parsing PostgreSQL procedure: {e}")
        return 1

    ASTS_DIR.mkdir(exist_ok=True, parents=True)
    ast_file = ASTS_DIR / "postgres_ast.json"
    with open(ast_file, "w", encoding="utf-8") as f:
        json.dump(ast, f, indent=2, ensure_ascii=False)

    logger.info(f"AST saved to: {ast_file}")
    return 0

if __name__ == "__main__":
    sys.exit(main())