from typing import Dict, Set

def build_global_normalization_map(*statement_mappings) -> Dict[str, str]:
    norm_map = {}
    for mapping in statement_mappings:
        for canonical, equivalents in mapping.items():
            canonical_key = canonical.upper().replace(' ', '_')
            norm_map[canonical.upper()] = canonical_key
            for eq in equivalents:
                norm_map[eq.upper()] = canonical_key
    return norm_map

def normalize_statement(stmt_type: str, normalization_map: Dict[str, str]) -> str:
    if not stmt_type:
        return ''
    return normalization_map.get(stmt_type.upper(), stmt_type.upper())

def collect_normalized_statements(ast: list, normalization_map: Dict[str, str]) -> Set[str]:
    stat_set = set()
    def recurse(statements):
        for stmt in statements:
            typ_raw = stmt.get('type', '')
            typ_norm = normalize_statement(typ_raw, normalization_map)
            if typ_norm:
                stat_set.add(typ_norm)
            for key in ['then', 'else', 'body', 'catch', 'statements', 'when', 'exception']:
                if key in stmt and isinstance(stmt[key], list):
                    recurse(stmt[key])
    for proc in ast:
        recurse(proc.get('statements', []))
    return stat_set

def avg_statements(ast: list) -> float:
    if not ast: return 0.0
    return round(sum(len(proc.get('statements', [])) for proc in ast) / len(ast), 2)

def find_antipatterns(ast: list) -> list:
    cursor_count = 0
    def recurse(statements):
        nonlocal cursor_count
        for stmt in statements:
            typ = stmt.get('type', '')
            typ_upper = typ.upper()
            if typ_upper.startswith('DECLARE_CURSOR') or typ_upper.startswith('DECLARE CURSOR'):
                cursor_count += 1
            for key in ['then', 'else', 'body', 'catch', 'statements', 'when', 'exception']:
                if key in stmt and isinstance(stmt[key], list):
                    recurse(stmt[key])
    for proc in ast:
        recurse(proc.get('statements', []))
    return ['Excessive cursor usage detected'] if cursor_count > 3 else []
