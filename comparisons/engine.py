from typing import Dict, List, Any, Set
import pandas as pd
from comparisons.adapters.dialect_adapter import DialectAdapter



class EnhancedASTComparisonEngine:
    def __init__(self, source_adapter, target_adapter):
        self.source_adapter = source_adapter
        self.target_adapter = target_adapter
        self.semantic_comparer = SemanticASTComparer(source_adapter, target_adapter)

    def compare_procedures(self, src_ast: List[Dict], tgt_ast: List[Dict]) -> Dict[str, Any]:
        results = {
            "comparison_metadata": {
                "source_procedures": len(src_ast),
                "target_procedures": len(tgt_ast),
                "comparison_timestamp": __import__('pandas').Timestamp.now().isoformat(),
            },
            "procedure_comparisons": [],
            "missing_procedures": [],
            "extra_procedures": [],
            "recommendations": []
        }

        source_procs = {self.source_adapter.normalize_procedure_name(p): p for p in src_ast}
        target_procs = {self.target_adapter.normalize_procedure_name(p): p for p in tgt_ast}


        source_names = set(source_procs.keys())
        target_names = set(target_procs.keys())

        matched = source_names & target_names
        missing = source_names - target_names
        extra = target_names - source_names

        results["missing_procedures"] = list(missing)
        results["extra_procedures"] = list(extra)

        for proc_name in matched:
            sproc = source_procs[proc_name]
            tproc = target_procs[proc_name]
            comparison = self.semantic_comparer.compare_procedures(sproc, tproc)
            results["procedure_comparisons"].append({ "procedure_name": proc_name, **comparison })

        results["recommendations"] = self._generate_recommendations(results)
        return results

    def _generate_recommendations(self, results: Dict) -> List[Dict]:
        recs = []
        if results['missing_procedures']:
            recs.append({
                "category": "Missing Procedures",
                "priority": "HIGH",
                "description": f"{len(results['missing_procedures'])} procedures missing in target",
                "action_items": [f"Implement procedure {p}" for p in results['missing_procedures']],
                "impact": "Critical"
            })
        # Add more heuristics here as needed
        return recs

    def compare_lineage(self, source_lineage: Dict, target_lineage: Dict) -> Dict:
        """
        Compare lineages with focus on source lineage (Sybase) usage and call hierarchy.
        Ignores target lineage except to find extras.
        """
        result = {
            "objects_missing_in_target": sorted(list(set(source_lineage) - set(target_lineage))),
            "objects_extra_in_target": sorted(list(set(target_lineage) - set(source_lineage))),
            "usage_differences": [],
            "call_hierarchy_differences": [],
            "cycle_differences": [],
            "anti_patterns": [],
        }

        src_call_graph = {k: v.get("calls", []) for k, v in source_lineage.items()}
        tgt_call_graph = {k: v.get("calls", []) for k, v in target_lineage.items()}

        def transitive_calls(call_map, root, visited=None):
            if visited is None: visited = set()
            if root in visited:
                return set()
            visited.add(root)
            res = set()
            for c in call_map.get(root, []):
                res.add(c)
                res.update(transitive_calls(call_map, c, visited.copy()))
            return res

        for obj in source_lineage.keys():
            src_deps = transitive_calls(src_call_graph, obj)
            tgt_deps = transitive_calls(tgt_call_graph, obj)
            if src_deps != tgt_deps:
                result["call_hierarchy_differences"].append({
                    "object": obj,
                    "source_deps": sorted(src_deps),
                    "target_deps": sorted(tgt_deps),
                })

        def find_cycles(call_map):
            cycles = []
            path = []
            visited = set()
            def dfs(node):
                if node in path:
                    cycles.append(path[path.index(node):] + [node])
                    return
                if node in visited:
                    return
                visited.add(node)
                path.append(node)
                for c in call_map.get(node, []):
                    dfs(c)
                path.pop()
            for node in call_map.keys():
                dfs(node)
            return cycles

        src_cycles = find_cycles(src_call_graph)
        tgt_cycles = find_cycles(tgt_call_graph)
        if set(map(tuple, src_cycles)) != set(map(tuple, tgt_cycles)):
            result["cycle_differences"].append({
                "source_cycles": src_cycles,
                "target_cycles": tgt_cycles
            })

        for obj, v in source_lineage.items():
            if v.get("type") == "table":
                usage = v.get("usage", {})
                if any("write" in ops for ops in usage.values()):
                    result["anti_patterns"].append(f"Source: Table {obj} written by one or more procs.")
        for obj, v in target_lineage.items():
            if v.get("type") == "table":
                usage = v.get("usage", {})
                if any("write" in ops for ops in usage.values()):
                    result["anti_patterns"].append(f"Target: Table {obj} written by one or more procs.")

        # Usage diffs stub, can be enhanced
        # TODO: add deep usage diff logic here

        return result

class SemanticASTComparer:
    def __init__(self, source_adapter, target_adapter):
        self.source_adapter = source_adapter
        self.target_adapter = target_adapter

    def compare_procedures(self, src_proc: Dict[str, Any], tgt_proc: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'parameters': self.compare_parameters(src_proc.get('params', []), tgt_proc.get('params', [])),
            'control_flow': self.compare_control_flow(src_proc.get('statements', []), tgt_proc.get('statements', [])),
            'loop_semantics': self.compare_loops(src_proc.get('statements', []), tgt_proc.get('statements', [])),
            'exception_handling': self.compare_exceptions(src_proc.get('statements', []), tgt_proc.get('statements', [])),
            'sql_semantics': self.compare_sql_statements(src_proc.get('statements', []), tgt_proc.get('statements', [])),
            'function_calls': self.compare_function_calls(src_proc.get('statements', []), tgt_proc.get('statements', [])),
        }

    def compare_parameters(self, src_params, tgt_params):
        matches, mismatches = [], []
        src_map = {p['name'].lower(): p for p in src_params}
        tgt_map = {p['name'].lower(): p for p in tgt_params}
        for n, s in src_map.items():
            if n in tgt_map:
                if self.source_adapter.types_compatible(s['type'], tgt_map[n]['type']):
                    matches.append(n)
                else:
                    mismatches.append(n)
            else:
                mismatches.append(n)
        return {'matched': matches, 'mismatched': mismatches}

    def compare_control_flow(self, src_stmts, tgt_stmts):
        def extract_branching(stmts):
            branches = []
            for s in stmts:
                t = s.get('type','').upper()
                if t == 'IF':
                    then_stmts = s.get('then', [])
                    else_stmts = s.get('else', [])
                    branches.append(('IF', s.get('condition'), extract_branching(then_stmts) + extract_branching(else_stmts)))
                for k in ['then','else','body','catch','statements','exception']:
                    if s.get(k): branches += extract_branching(s[k])
            return branches

        return {
            'match': sorted(map(str, extract_branching(src_stmts))) == sorted(map(str, extract_branching(tgt_stmts))),
        }

    def compare_loops(self, src_stmts, tgt_stmts):
        def collect_loops(stmts):
            loops = []
            for s in stmts:
                if s.get('type','').upper() == 'WHILE':
                    loops.append(s.get('condition'))
                for k in ['body','statements']:
                    if s.get(k): loops += collect_loops(s[k])
            return loops

        s_loops = collect_loops(src_stmts)
        t_loops = collect_loops(tgt_stmts)
        return {'match': set(s_loops) == set(t_loops), 'src_loops': s_loops, 'tgt_loops': t_loops}

    def compare_exceptions(self, src_stmts, tgt_stmts):
        def get_exceptions(stmts):
            exc = []
            for s in stmts:
                typ = s.get('type','').upper()
                if typ in ['TRY', 'BEGIN', 'CATCH', 'EXCEPTION']:
                    exc.append(typ)
                for k in ['body','catch','exception','statements']:
                    if s.get(k): exc += get_exceptions(s[k])
            return exc

        s_exc = get_exceptions(src_stmts)
        t_exc = get_exceptions(tgt_stmts)
        return {'match': s_exc == t_exc, 'src': s_exc, 'tgt': t_exc}

    def compare_sql_statements(self, src_stmts, tgt_stmts):
        def extract_sql(slist):
            sqls = []
            for s in slist:
                sqls.append(s.get('query') or s.get('command') or '')
                for k in ['then','else','body']:
                    if s.get(k): sqls += extract_sql(s[k])
            return sqls
        s_sql = set(extract_sql(src_stmts))
        t_sql = set(extract_sql(tgt_stmts))
        return {'match': s_sql == t_sql, 'src_sqls': list(s_sql), 'tgt_sqls': list(t_sql)}

    def compare_function_calls(self, src_stmts, tgt_stmts):
        def extract_calls(stmts):
            calls = []
            for s in stmts:
                if 'command' in s:
                    calls.append(s['command'])
                for k in ['then','else','body','catch','statements','exception']:
                    if k in s and isinstance(s[k], list):
                        calls += extract_calls(s[k])
            return calls
        src_calls = set(extract_calls(src_stmts))
        tgt_calls = set(extract_calls(tgt_stmts))
        common = src_calls & tgt_calls
        return {'mapped': list(common), 'src_only': list(src_calls - common), 'tgt_only': list(tgt_calls - common)}

class EnhancedASTComparisonEngineV2(EnhancedASTComparisonEngine):
    def __init__(self, source_adapter, target_adapter):
        super().__init__(source_adapter, target_adapter)
        self.semantic_comparer = SemanticASTComparer(source_adapter, target_adapter)
