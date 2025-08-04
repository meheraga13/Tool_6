from .base_parser import BaseSQLParser
from .postgresql_parser import PostgreSQLParser
# from .mysql_parser import MySQLParser  # Add as needed

PARSERS = [
    PostgreSQLParser(),
    # MySQLParser(),
]


def get_parser_for_dialect(dialect_name: str) -> BaseSQLParser:
    lowered = dialect_name.strip().lower()
    for parser in PARSERS:
        if parser.supports_dialect(lowered):
            return parser
    raise ValueError(f"No parser found for dialect '{dialect_name}'")
