import logging
from typing import List, Dict, Optional

from antlr4 import InputStream, CommonTokenStream
from antlr4.error.ErrorListener import ErrorListener
from antlr4.error.ErrorStrategy import BailErrorStrategy
from jsonschema import validate

from .base_parser import BaseSQLParser  # Adjust to your base parser class if named differently
from generated.PostgreSQLLexer import PostgreSQLLexer
from generated.PostgreSQLParser import PostgreSQLParser as AntlrSQLParser
from .postgresql_ast_visitor import PgASTVisitor  # Your visitor class

logger = logging.getLogger(__name__)


class PostgreSQLParserError(Exception):
    pass


class ANTLRErrorListener(ErrorListener):
    def __init__(self):
        super().__init__()
        self.errors = []
        self.has_errors = False

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        error_msg = f"Line {line}, Col {column}: {msg}"
        self.errors.append(error_msg)
        self.has_errors = True
        logger.error(f"ANTLR Syntax Error: {error_msg}")


class PostgreSQLParser(BaseSQLParser):
    def __init__(self):
        super().__init__()
        self.ast_schema = self._load_schema()

    def supports_dialect(self, dialect_name: str) -> bool:
        return dialect_name.lower() in {"postgresql", "pgsql", "postgres"}

    def parse(self, sql_content: str) -> List[Dict]:
        ast = self._parse_with_antlr(sql_content)
        if ast is None:
            raise PostgreSQLParserError("ANTLR parsing failed; no fallback available.")

        try:
            validate(instance=ast, schema=self.ast_schema)
        except Exception as ex:
            logger.error(f"AST validation failed: {ex}")
            raise PostgreSQLParserError(str(ex))

        logger.info("Parsing and validation successful.")
        return ast

    def _load_schema(self) -> dict:
        # Insert your full JSON schema here; this is a shortened example:
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Stored Procedure AST",
            "type": "array",
            "items": {
                "type": "object",
                "required": ["proc_name", "params", "return_type", "variables", "statements"],
                "properties": {
                    "proc_name": {"type": "string"},
                    "params": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["name", "type"],
                            "properties": {
                                "name": {"type": "string", "minLength": 1},
                                "type": {"type": "string", "minLength": 1},
                                "mode": {
                                    "type": "string",
                                    "enum": ["IN", "OUT", "INOUT"],
                                    "default": "IN",
                                },
                            },
                            "additionalProperties": False,
                        },
                    },
                    "return_type": {"type": "string"},
                    "variables": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["name", "type"],
                            "properties": {
                                "name": {"type": "string", "minLength": 1},
                                "type": {"type": "string", "minLength": 1},
                            },
                            "additionalProperties": False,
                        },
                    },
                    "statements": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["type"],
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": [
                                        "SET",
                                        "UPDATE",
                                        "SELECT_INTO",
                                        "DECLARE_CURSOR",
                                        "OPEN_CURSOR",
                                        "FETCH_CURSOR",
                                        "CLOSE_CURSOR",
                                        "DEALLOCATE_CURSOR",
                                        "RETURN",
                                        "IF",
                                        "WHILE",
                                        "FOR_CURSOR_LOOP",
                                        "RAISE",
                                        "TRY",
                                        "EXCEPTION_HANDLER",
                                        "EXECUTE_PROCEDURE",
                                        "INSERT",
                                        "DELETE",
                                        "CREATE_TEMP_TABLE",
                                        "EXECUTE_DYNAMIC",
                                        "COMMIT",
                                        "ROLLBACK",
                                    ],
                                },
                            },
                            "additionalProperties": True,
                        },
                    },
                },
                "additionalProperties": False,
            },
        }

    def _parse_with_antlr(self, sql_content: str) -> Optional[List[Dict]]:
        try:
            input_stream = InputStream(sql_content)
            lexer = PostgreSQLLexer(input_stream)
            token_stream = CommonTokenStream(lexer)
            parser = AntlrSQLParser(token_stream)

            error_listener = ANTLRErrorListener()
            parser.removeErrorListeners()
            parser.addErrorListener(error_listener)

            # Use BailErrorStrategy for immediate failure on syntax errors
            parser._errHandler = BailErrorStrategy()

            tree = parser.root()  # Your grammar's entry point rule

            if error_listener.has_errors:
                logger.error(f"ANTLR syntax errors: {error_listener.errors}")
                return None

            visitor = PgASTVisitor()
            ast = visitor.visit(tree)

            if isinstance(ast, dict):
                return [ast]
            return ast

        except Exception as e:
            logger.error(f"ANTLR parsing exception: {e}")
            return None
