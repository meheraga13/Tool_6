#!/usr/bin/env python3

import sys
import json
import logging
from pathlib import Path
from typing import Dict

sys.path.append(str(Path(__file__).parent.parent))

from config import *
from comparisons.adapters import dialect_adapter
from comparisons.engine import EnhancedASTComparisonEngine
from comparisons.normalization import (
    avg_statements,
    find_antipatterns,
    collect_normalized_statements,
    build_global_normalization_map,
)

logger = logging.getLogger(__name__)
logging.basicConfig(**LOGGING_CONFIG)


def load_json(path: Path) -> Dict:
    if not path.exists():
        logger.error(f"File not found: {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved file to {path}")


def generate_report(results: Dict) -> str:
    lines = []
    lines.append("=" * 80)
    lines.append("ENHANCED AST COMPARISON REPORT")
    lines.append("=" * 80)
    lines.append("")
    meta = results.get("comparison_metadata", {})
    lines.append(f"Comparison Date: {meta.get('comparison_timestamp', 'N/A')}")
    lines.append(f"Sybase Procedures: {meta.get('source_procedures', 0)}")
    lines.append(f"PostgreSQL Procedures: {meta.get('target_procedures', 0)}")
    lines.append("")

    missing = results.get("missing_procedures", [])
    if missing:
        lines.append("Missing Procedures in PostgreSQL:")
        for p in missing:
            lines.append(f"  • {p}")
    else:
        lines.append("No missing procedures in PostgreSQL.")
    lines.append("")

    struct = results.get("structural_analysis", {})
    lines.append("STRUCTURAL ANALYSIS:")
    lines.append(f"  Average Statements per Procedure:")
    lines.append(f"    Sybase: {struct.get('avg_statements_sybase', 'N/A')}")
    lines.append(f"    PostgreSQL: {struct.get('avg_statements_postgres', 'N/A')}")
    antipatterns = struct.get("anti_patterns", [])
    if antipatterns:
        lines.append("  Anti-patterns Detected:")
        for ap in antipatterns:
            lines.append(f"    • {ap}")
    else:
        lines.append("  No antipatterns detected.")
    lines.append("")

    trans = results.get("transformation_analysis", {})
    syb_only = trans.get("sybase_only_statements", [])
    pg_only = trans.get("postgresql_only_statements", [])
    if syb_only or pg_only:
        lines.append("TRANSFORMATION ANALYSIS:")
        if syb_only:
            lines.append("  Sybase-only statements:")
            for stmt in syb_only:
                lines.append(f"    • {stmt}")
        if pg_only:
            lines.append("  PostgreSQL-only statements:")
            for stmt in pg_only:
                lines.append(f"    • {stmt}")
    else:
        lines.append("  No dialect-specific statement differences found.")
    lines.append("")

    lines.append("SEMANTIC PROCEDURE COMPARISON:")
    for proc_comp in results.get("procedure_comparisons", []):
        lines.append(f"Procedure: {proc_comp['procedure_name']}")
        for section, comp_res in proc_comp.items():
            if section == "procedure_name":
                continue
            lines.append(f"  {section}:")
            lines.append(f"    {comp_res}")
        lines.append("")

    lineage = results.get("lineage_analysis", {})
    if lineage:
        lines.append("LINEAGE ANALYSIS (SYBASE):")
        if lineage.get("objects_missing_in_target"):
            lines.append("  Objects missing in target lineage:")
            for obj in lineage["objects_missing_in_target"]:
                lines.append(f"    • {obj}")
        if lineage.get("objects_extra_in_target"):
            lines.append("  Objects extra in target lineage:")
            for obj in lineage["objects_extra_in_target"]:
                lines.append(f"    • {obj}")
        if lineage.get("usage_differences"):
            lines.append("  Usage differences:")
            for diff in lineage["usage_differences"]:
                lines.append(f"    Object: {diff.get('object', '(unknown)')}")
                if "details" in diff and isinstance(diff["details"], dict):
                    for proc, usages in diff["details"].items():
                        src_usage = usages.get('source_usage', [])
                        tgt_usage = usages.get('target_usage', [])
                        lines.append(f"      Procedure: {proc}")
                        lines.append(f"        Source Usage: {', '.join(src_usage)}")
                        lines.append(f"        Target Usage: {', '.join(tgt_usage)}")
                else:
                    lines.append("      (No detailed usage info available)")
        if lineage.get("call_hierarchy_differences"):
            lines.append("  Call Hierarchy Differences:")
            for diff in lineage["call_hierarchy_differences"]:
                lines.append(f"    Object: {diff.get('object', '(unknown)')}")
                source_deps = diff.get('source_deps') or diff.get('source_transitive_deps', [])
                target_deps = diff.get('target_deps') or diff.get('target_transitive_deps', [])
                lines.append(f"      Source deps: {', '.join(source_deps) if source_deps else '(none)'}")
                lines.append(f"      Target deps: {', '.join(target_deps) if target_deps else '(none)'}")
        if lineage.get("cycle_differences"):
            lines.append("  Cycles detected differences:")
            for diff in lineage["cycle_differences"]:
                src_cycles = diff.get('source_cycles', [])
                tgt_cycles = diff.get('target_cycles', [])
                lines.append(f"    Source cycles: {src_cycles if src_cycles else '(none)'}")
                lines.append(f"    Target cycles: {tgt_cycles if tgt_cycles else '(none)'}")
        if lineage.get("anti_patterns"):
            lines.append("  Lineage Anti-Patterns:")
            for ap in lineage["anti_patterns"]:
                lines.append(f"    • {ap}")
        lines.append("")

    recs = results.get("recommendations", [])
    if recs:
        lines.append("RECOMMENDATIONS:")
        current_priority = None
        for rec in recs:
            if rec.get("priority") != current_priority:
                lines.append("")
                lines.append(f"{rec.get('category', 'General')} (Priority: {rec.get('priority', 'N/A')}):")
                current_priority = rec.get("priority")
            lines.append(f"  - {rec.get('description')}")
            if rec.get("action_items"):
                lines.append("    Action Items:")
                for item in rec.get("action_items", []):
                    lines.append(f"      - {item}")
            if rec.get("impact"):
                lines.append(f"    Impact: {rec.get('impact')}")
        lines.append("")
    else:
        lines.append("No recommendations.")
    lines.append("")
    lines.append("=" * 80)

    return "\n".join(lines)


def main():
    try:
        sybase_ast_path = ASTS_DIR / "sybase_ast.json"
        postgres_ast_path = ASTS_DIR / "postgres_ast.json"
        sybase_lineage_path = LINEAGE_DIR / "sybase_lineage.json"
        dialect_config_path = PROJECT_ROOT / "config" / "dialects.yaml"

        sybase_ast = load_json(sybase_ast_path)
        postgres_ast = load_json(postgres_ast_path)
        sybase_lineage = load_json(sybase_lineage_path)

        source_adapter = dialect_adapter.DialectAdapter("sybase", dialect_config_path)
        target_adapter = dialect_adapter.DialectAdapter("postgresql", dialect_config_path)

        engine = EnhancedASTComparisonEngine(source_adapter, target_adapter)

        results = engine.compare_procedures(sybase_ast, postgres_ast)

        results["structural_analysis"] = {
            "avg_statements_sybase": avg_statements(sybase_ast),
            "avg_statements_postgres": avg_statements(postgres_ast),
            "anti_patterns": find_antipatterns(sybase_ast),
        }

        global_norm_map = build_global_normalization_map(
            source_adapter.statement_mappings,
            target_adapter.statement_mappings,
        )
        sybase_stmt_set = collect_normalized_statements(sybase_ast, global_norm_map)
        postgres_stmt_set = collect_normalized_statements(postgres_ast, global_norm_map)
        results["transformation_analysis"] = {
            "sybase_only_statements": sorted(list(sybase_stmt_set.difference(postgres_stmt_set))),
            "postgresql_only_statements": sorted(list(postgres_stmt_set.difference(sybase_stmt_set))),
        }

        # Only Sybase lineage used for call dependencies, hierarchy, etc.
        results["lineage_analysis"] = engine.compare_lineage(sybase_lineage, {})

        output_json_path = REPORTS_DIR / "enhanced_comparison_results.json"
        save_json(results, output_json_path)

        report_text = generate_report(results)
        print(report_text)

        output_report_path = REPORTS_DIR / "enhanced_comparison_results.txt"
        with open(output_report_path, "w", encoding="utf-8") as f:
            f.write(report_text)

        logger.info(f"Analysis complete. Reports saved to {REPORTS_DIR}")
        return 0

    except Exception as e:
        logger.exception("Failed during AST and lineage comparison.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
