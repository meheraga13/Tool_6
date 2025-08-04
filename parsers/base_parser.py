from typing import List, Dict, Any

class BaseSQLParser:
    """
    Abstract base class for SQL dialect parsers.
    """
    def parse(self, sql_content: str) -> List[Dict[str, Any]]:
        """
        Parse SQL content and return list of standardized AST nodes.
        """
        raise NotImplementedError()

    def supports_dialect(self, dialect_name: str) -> bool:
        """
        Return True if this parser supports the given dialect.
        """
        raise NotImplementedError()
