from typing import List
import yaml

class DialectAdapter:
    def __init__(self, dialect_name: str, config_path: str):
        self.dialect_name = dialect_name
        with open(config_path, "r", encoding="utf-8") as f:
            full_cfg = yaml.safe_load(f)
        config = full_cfg.get('dialects', {}).get(dialect_name, {})
        self.type_mappings = config.get('type_mappings', {})
        self.statement_mappings = config.get('statement_mappings', {})
        self.type_norm_map = self._build_norm_map(self.type_mappings)
        self.statement_norm_map = self._build_norm_map(self.statement_mappings)

    def _build_norm_map(self, mapping):
        norm_map = {}
        for canonical, aliases in mapping.items():
            canonical_key = canonical.upper().replace(' ', '_')
            norm_map[canonical_key] = canonical_key
            for alias in aliases:
                norm_map[alias.upper().replace(' ', '_')] = canonical_key
        return norm_map

    def normalize_statement(self, stmt: str) -> str:
        return self.statement_norm_map.get(stmt.upper().replace(' ', '_'), stmt.upper().replace(' ', '_'))

    def normalize_type(self, typ: str) -> str:
        return self.type_norm_map.get(typ.upper().replace(' ', '_'), typ.upper().replace(' ', '_'))

    def normalize_procedure_name(self, proc: dict) -> str:
        return proc.get('name', proc.get('proc_name', '')).lower()

    def normalize_parameter(self, param: dict) -> dict:
        norm_type = self.normalize_type(param.get('type', ''))
        return {**param, 'type': norm_type}

    def types_compatible(self, src_type: str, tgt_type: str) -> bool:
        return self.normalize_type(src_type) == self.normalize_type(tgt_type)

    def is_equivalent_function(self, func_name: str, func_list: List[str]) -> bool:
        norm_func = self.normalize_statement(func_name)
        return any(self.normalize_statement(f) == norm_func for f in func_list)
