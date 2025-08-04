from typing import List, Dict, Optional
from generated.PostgreSQLParser import PostgreSQLParser
from generated.PostgreSQLParserVisitor import PostgreSQLParserVisitor
import re


class PgASTVisitor(PostgreSQLParserVisitor):

    def visitRoot(self, ctx):
        # Visit stmtblock explicitly
        return self.visit(ctx.stmtblock())

    def visitStmtblock(self, ctx):
        return self.visit(ctx.stmtmulti())

    def visitStmtmulti(self, ctx):
        results = []
        for stmt_ctx in ctx.stmt():
            if stmt_ctx:
                res = self.visit(stmt_ctx)
                if res is not None:
                    # Collect or filter as needed
                    if isinstance(res, list):
                        results.extend(res)
                    else:
                        results.append(res)
        return results

    # Your existing visitStmt etc.
