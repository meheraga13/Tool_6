#!/usr/bin/env python3
"""
Final Validation Report Generator.
Consolidates all validation results into a comprehensive markdown report.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from jinja2 import Template

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from config import *

# Setup logging
logging.basicConfig(**LOGGING_CONFIG)
logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates comprehensive validation reports."""
    
    def __init__(self):
        self.report_data = {}
        self.charts_dir = REPORTS_DIR / "charts"
        self.charts_dir.mkdir(exist_ok=True)
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        
        report_data = {
            "metadata": {
                "generation_time": datetime.now().isoformat(),
                "report_version": "1.0",
                "validation_pipeline": "Sybase to PostgreSQL"
            },
            "executive_summary": {},
            "ast_analysis": {},
            "test_generation": {},
            "execution_results": {},
            "lineage_analysis": {},
            "recommendations": [],
            "appendices": {}
        }
        
        try:
            # Load all validation results
            report_data = self._load_validation_results(report_data)
            
            # Generate executive summary
            report_data["executive_summary"] = self._generate_executive_summary(report_data)
            
            # Generate visualization charts
            self._generate_charts(report_data)
            
            # Generate recommendations based on analysis
            report_data["recommendations"] = self._generate_recommendations(report_data)
            
            # Create markdown report content
            markdown_report = self._create_markdown_report(report_data)
            
            # Save JSON and Markdown reports
            self._save_reports(report_data, markdown_report)
            
            logger.info("Comprehensive validation report generated successfully")
            
        except Exception as e:
            logger.error(f"Report generation failed: {str(e)}")
            raise
        
        return report_data
    
    def _load_validation_results(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Load all validation results from previous steps."""
        
        # Load AST comparison results
        ast_comparison_file = REPORTS_DIR / "ast_comparison_results.json"
        if ast_comparison_file.exists():
            with open(ast_comparison_file, 'r', encoding='utf-8') as f:
                report_data["ast_analysis"] = json.load(f)
            logger.info("Loaded AST comparison results")
        
        # Load test generation results
        test_metadata_file = PROJECT_ROOT / "tests" / "test_metadata.json"
        test_summary_file = PROJECT_ROOT / "tests" / "generation_summary.json"
        
        if test_metadata_file.exists() and test_summary_file.exists():
            with open(test_metadata_file, 'r', encoding='utf-8') as f:
                test_metadata = json.load(f)
            with open(test_summary_file, 'r', encoding='utf-8') as f:
                test_summary = json.load(f)
            
            report_data["test_generation"] = {
                "metadata": test_metadata,
                "summary": test_summary
            }
            logger.info("Loaded test generation results")
        
        # Load test execution results
        execution_results_file = REPORTS_DIR / "test_execution_results.json"
        if execution_results_file.exists():
            with open(execution_results_file, 'r', encoding='utf-8') as f:
                report_data["execution_results"] = json.load(f)
            logger.info("Loaded test execution results")
        
        # Load lineage analysis
        sybase_lineage_file = LINEAGE_DIR / "sybase_lineage.json"
        postgres_lineage_file = LINEAGE_DIR / "postgres_lineage.json"
        
        lineage_data = {}
        if sybase_lineage_file.exists():
            with open(sybase_lineage_file, 'r', encoding='utf-8') as f:
                lineage_data["sybase"] = json.load(f)
        
        if postgres_lineage_file.exists():
            with open(postgres_lineage_file, 'r', encoding='utf-8') as f:
                lineage_data["postgres"] = json.load(f)
        
        if lineage_data:
            report_data["lineage_analysis"] = lineage_data
            logger.info("Loaded lineage analysis")
        
        return report_data
    
    def _generate_executive_summary(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary from all validation results."""
        
        summary = {
            "overall_status": "unknown",
            "transformation_quality": 0.0,
            "test_coverage": 0.0,
            "critical_issues": 0,
            "warnings": 0,
            "key_metrics": {},
            "deployment_readiness": "not_ready"
        }
        
        # Analyze AST comparison results
        if "ast_analysis" in report_data:
            ast_data = report_data["ast_analysis"]
            summary["transformation_quality"] = ast_data.get("overall_similarity", 0.0)
            summary["critical_issues"] += len(ast_data.get("critical_differences", []))
            summary["warnings"] += len(ast_data.get("warnings", []))
        
        # Analyze test execution results
        if "execution_results" in report_data:
            exec_data = report_data["execution_results"]
            exec_summary = exec_data.get("execution_summary", {})
            
            total_tests = exec_summary.get("total_tests", 0)
            successful_tests = exec_summary.get("successful_tests", 0)
            
            if total_tests > 0:
                summary["test_coverage"] = successful_tests / total_tests
            
            # Count issues from execution
            issues = exec_data.get("issues_found", [])
            summary["critical_issues"] += len([i for i in issues if i.get("severity") == "critical"])
            summary["warnings"] += len([i for i in issues if i.get("severity") == "warning"])
        
        # Analyze test generation
        if "test_generation" in report_data:
            test_data = report_data["test_generation"]
            test_summary = test_data.get("summary", {})
            summary["key_metrics"]["procedures_tested"] = test_summary.get("tests_generated", 0)
            summary["key_metrics"]["avg_test_cases"] = test_summary.get("test_cases_per_procedure", 0)
        
        # Determine overall status
        if summary["critical_issues"] == 0 and summary["transformation_quality"] >= 0.9 and summary["test_coverage"] >= 0.9:
            summary["overall_status"] = "excellent"
            summary["deployment_readiness"] = "ready"
        elif summary["critical_issues"] <= 2 and summary["transformation_quality"] >= 0.8 and summary["test_coverage"] >= 0.8:
            summary["overall_status"] = "good"
            summary["deployment_readiness"] = "ready_with_review"
        elif summary["critical_issues"] <= 5 and summary["transformation_quality"] >= 0.6:
            summary["overall_status"] = "fair"
            summary["deployment_readiness"] = "needs_work"
        else:
            summary["overall_status"] = "poor"
            summary["deployment_readiness"] = "not_ready"
        
        return summary
    
    def _generate_recommendations(self, report_data: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on validation data."""
        recs = []
        
        summary = report_data.get("executive_summary", {})
        key_metrics = summary.get("key_metrics", {})
        crit_issues = summary.get("critical_issues", 0)
        warnings = summary.get("warnings", 0)
        coverage = summary.get("test_coverage", 0)
        quality = summary.get("transformation_quality", 0)
        readiness = summary.get("deployment_readiness", "not_ready")
        
        if crit_issues > 0:
            recs.append(f"⚠️ Critical issues detected: {crit_issues}. Immediate review recommended.")
        if warnings > 0:
            recs.append(f"⚠️ Warnings present: {warnings}. Review warnings for potential risks.")
        if coverage < 0.8:
            recs.append(f"⚠️ Test coverage low ({coverage:.0%}). Consider adding more test cases.")
        if quality < 0.8:
            recs.append(f"⚠️ Transformation quality score low ({quality:.0%}). Investigate procedural differences.")
        if readiness in ["needs_work", "not_ready"]:
            recs.append(f"⚠️ Deployment readiness status: {readiness}. Additional validation required.")
        if readiness == "ready" or readiness == "ready_with_review":
            recs.append("✅ Migration pipeline indicates deployment readiness.")
        
        if not recs:
            recs.append("✅ No significant issues found. Migration pipeline passed all checks.")
        
        return recs
    
    def _generate_charts(self, report_data: Dict[str, Any]) -> None:
        """Generate visualization charts for the report."""
        
        # Set style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # Chart 1: Transformation Quality Overview
        self._create_quality_overview_chart(report_data)
        
        # Chart 2: Test Execution Results
        self._create_test_results_chart(report_data)
        
        # Chart 3: Performance Comparison
        self._create_performance_chart(report_data)
        
        # Chart 4: Issue Distribution
        self._create_issues_chart(report_data)
        
        # Chart 5: Lineage Coverage
        self._create_lineage_chart(report_data)
        
        logger.info(f"Generated visualization charts in {self.charts_dir}")
    
    def _create_quality_overview_chart(self, report_data: Dict[str, Any]) -> None:
        """Create transformation quality overview chart."""
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Transformation Quality Overview', fontsize=16, fontweight='bold')
        
        # Overall similarity gauge
        if "ast_analysis" in report_data:
            similarity = report_data["ast_analysis"].get("overall_similarity", 0.0)
            
            ax1.pie(
                [similarity, 1 - similarity],
                startangle=90,
                counterclock=False, 
                colors=['green' if similarity >= 0.8 else 'orange' if similarity >= 0.6 else 'red', 'lightgray'],
                wedgeprops=dict(width=0.3)
            )
            ax1.set_title(f'Overall Similarity: {similarity:.1%}')
        
        # Test success rate
        if "execution_results" in report_data:
            exec_summary = report_data["execution_results"].get("execution_summary", {})
            total = exec_summary.get("total_tests", 1)
            success = exec_summary.get("successful_tests", 0)
            failed = exec_summary.get("failed_tests", 0)
            
            ax2.pie(
                [success, failed],
                labels=['Passed', 'Failed'],
                autopct='%1.1f%%',
                colors=['green', 'red']
            )
            ax2.set_title('Test Execution Results')
        
        # Procedure comparison histogram
        if "ast_analysis" in report_data and "procedure_comparisons" in report_data["ast_analysis"]:
            comparisons = report_data["ast_analysis"]["procedure_comparisons"]
            similarities = [comp.get("similarity_score", 0) for comp in comparisons if "similarity_score" in comp]
            
            ax3.hist(similarities, bins=10, alpha=0.7, color='skyblue', edgecolor='black')
            ax3.set_xlabel('Similarity Score')
            ax3.set_ylabel('Number of Procedures')
            ax3.set_title('Procedure Similarity Distribution')
            ax3.axvline(x=0.8, color='green', linestyle='--', label='Target (80%)')
            ax3.legend()
        
        # Issues summary
        if "execution_results" in report_data:
            issues = report_data["execution_results"].get("issues_found", [])
            issue_types = {}
            for issue in issues:
                issue_type = issue.get("type", "unknown")
                issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
            
            if issue_types:
                ax4.bar(range(len(issue_types)), list(issue_types.values()))
                ax4.set_xticks(range(len(issue_types)))
                ax4.set_xticklabels(list(issue_types.keys()), rotation=45, ha='right')
                ax4.set_ylabel('Count')
                ax4.set_title('Issue Distribution')
            else:
                ax4.text(0.5, 0.5, 'No issues reported', ha='center', va='center')
        else:
            ax4.text(0.5, 0.5, 'No execution results for issues', ha='center', va='center')
        
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        chart_path = self.charts_dir / "transformation_quality_overview.png"
        fig.savefig(chart_path)
        plt.close(fig)

    def _create_test_results_chart(self, report_data: Dict[str, Any]) -> None:
        """Create detailed test results chart."""
        if "execution_results" not in report_data:
            return
        
        data = report_data["execution_results"].get("test_cases", [])
        if not data:
            return
        
        df = pd.DataFrame(data)
        if df.empty or "result" not in df.columns:
            return
        
        result_counts = df['result'].value_counts()
        
        plt.figure(figsize=(8,6))
        sns.barplot(x=result_counts.index, y=result_counts.values, palette='muted')
        plt.title('Test Case Results')
        plt.xlabel('Result')
        plt.ylabel('Count')
        
        chart_path = self.charts_dir / "test_results.png"
        plt.savefig(chart_path)
        plt.close()

    def _create_performance_chart(self, report_data: Dict[str, Any]) -> None:
        """Create performance metrics chart."""
        if "execution_results" not in report_data:
            return
        
        perf_data = report_data["execution_results"].get("performance_metrics", [])
        if not perf_data:
            return
        
        df = pd.DataFrame(perf_data)
        if df.empty:
            return
        
        plt.figure(figsize=(10,6))
        sns.lineplot(data=df, x='test_case', y='execution_time_ms')
        plt.title('Test Case Execution Time (ms)')
        plt.xlabel('Test Case')
        plt.ylabel('Execution Time (ms)')
        
        chart_path = self.charts_dir / "performance_metrics.png"
        plt.savefig(chart_path)
        plt.close()

    def _create_issues_chart(self, report_data: Dict[str, Any]) -> None:
        """Create issue count by severity chart."""
        if "execution_results" not in report_data:
            return
        
        issues = report_data["execution_results"].get("issues_found", [])
        if not issues:
            return
        
        severity_counts = {}
        for issue in issues:
            sev = issue.get("severity", "unknown")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        if not severity_counts:
            return
        
        plt.figure(figsize=(8,6))
        sns.barplot(x=list(severity_counts.keys()), y=list(severity_counts.values()), palette='coolwarm')
        plt.title('Issues by Severity')
        plt.xlabel('Severity')
        plt.ylabel('Count')
        
        chart_path = self.charts_dir / "issues_by_severity.png"
        plt.savefig(chart_path)
        plt.close()

    def _create_lineage_chart(self, report_data: Dict[str, Any]) -> None:
        """Create a simple lineage coverage chart."""
        lineage_data = report_data.get("lineage_analysis", {})
        if not lineage_data:
            return
        
        counts = {}
        for platform, data in lineage_data.items():
            proc_count = sum(1 for k, v in data.items() if v.get("type") == "procedure")
            table_count = sum(1 for k, v in data.items() if v.get("type") == "table")
            counts[platform] = {"procedures": proc_count, "tables": table_count}
        
        df = pd.DataFrame(counts).T
        
        plt.figure(figsize=(8,6))
        df.plot(kind='bar', stacked=False)
        plt.title('Lineage Coverage by Platform')
        plt.xlabel('Platform')
        plt.ylabel('Count')
        plt.xticks(rotation=0)
        plt.legend(title='Object Type')
        
        chart_path = self.charts_dir / "lineage_coverage.png"
        plt.savefig(chart_path)
        plt.close()
    
    def _create_markdown_report(self, report_data: Dict[str, Any]) -> str:
        """Generate a Markdown report consolidating all sections."""
        md = []
        md.append(f"# Stored Procedure Transformation Validation Report\n")
        md.append(f"**Generated:** {report_data['metadata']['generation_time']}\n")
        md.append(f"**Pipeline Version:** {report_data['metadata']['report_version']}\n")
        md.append(f"---\n")
        
        # Executive Summary
        summary = report_data.get("executive_summary", {})
        md.append(f"## Executive Summary\n")
        md.append(f"- **Overall Status:** {summary.get('overall_status', 'N/A')}")
        md.append(f"- **Transformation Quality:** {summary.get('transformation_quality', 0):.2%}")
        md.append(f"- **Test Coverage:** {summary.get('test_coverage', 0):.2%}")
        md.append(f"- **Critical Issues:** {summary.get('critical_issues', 0)}")
        md.append(f"- **Warnings:** {summary.get('warnings', 0)}")
        md.append(f"- **Deployment Readiness:** {summary.get('deployment_readiness', 'N/A')}\n")
        
        # Insert images of charts
        md.append("## Visualization Charts\n")
        charts = [
            "transformation_quality_overview.png",
            "test_results.png",
            "performance_metrics.png",
            "issues_by_severity.png",
            "lineage_coverage.png"
        ]
        for chart_file in charts:
            chart_path = f"./charts/{chart_file}"
            md.append(f"![{chart_file}]({chart_path})\n")
        
        # AST Analysis summary
        ast_analysis = report_data.get("ast_analysis", {})
        md.append("## AST Comparison Analysis\n")
        if ast_analysis:
            overall_similarity = ast_analysis.get("overall_similarity", None)
            if overall_similarity is not None:
                md.append(f"- Overall Similarity Score: {overall_similarity:.2%}")
            crit_diffs = ast_analysis.get("critical_differences", [])
            warnings = ast_analysis.get("warnings", [])
            md.append(f"- Critical Differences Found: {len(crit_diffs)}")
            md.append(f"- Warnings Found: {len(warnings)}")
        else:
            md.append("No AST analysis data available.\n")
        
        # Test Generation summary
        test_gen = report_data.get("test_generation", {})
        md.append("## Test Generation Summary\n")
        if test_gen and "summary" in test_gen:
            summary = test_gen["summary"]
            md.append(f"- Procedures Tested: {summary.get('tests_generated', 0)}")
            md.append(f"- Average Test Cases per Procedure: {summary.get('test_cases_per_procedure', 0):.2f}\n")
        else:
            md.append("No test generation data available.\n")
        
        # Execution Results summary
        exec_results = report_data.get("execution_results", {})
        md.append("## Test Execution Results\n")
        if exec_results and "execution_summary" in exec_results:
            exec_summary = exec_results["execution_summary"]
            md.append(f"- Total Tests Run: {exec_summary.get('total_tests', 0)}")
            md.append(f"- Successful Tests: {exec_summary.get('successful_tests', 0)}")
            md.append(f"- Failed Tests: {exec_summary.get('failed_tests', 0)}\n")
        else:
            md.append("No test execution data available.\n")
        
        # Lineage Analysis
        lineage = report_data.get("lineage_analysis", {})
        md.append("## Data Lineage Analysis\n")
        if lineage:
            for platform in ["sybase", "postgres"]:
                plat_data = lineage.get(platform, {})
                if plat_data:
                    md.append(f"### {platform.capitalize()} Lineage\n")
                    proc_count = sum(1 for k,v in plat_data.items() if v.get("type") == "procedure")
                    tbl_count = sum(1 for k,v in plat_data.items() if v.get("type") == "table")
                    md.append(f"- Procedures: {proc_count}")
                    md.append(f"- Tables: {tbl_count}\n")
        else:
            md.append("No lineage analysis data available.\n")
        
        # Recommendations
        recommendations = report_data.get("recommendations", [])
        md.append("## Recommendations\n")
        if recommendations:
            for rec in recommendations:
                md.append(f"- {rec}")
        else:
            md.append("No recommendations provided.\n")
        
        return "\n".join(md)
    
    def _save_reports(self, report_data: Dict[str, Any], markdown_report: str) -> None:
        """Save JSON and Markdown reports to disk."""
        REPORTS_DIR.mkdir(exist_ok=True)
        
        json_path = REPORTS_DIR / "final_validation_report.json"
        md_path = REPORTS_DIR / "final_validation_report.md"
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved final report JSON to: {json_path}")
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(markdown_report)
        logger.info(f"Saved final report Markdown to: {md_path}")


def main():
    rg = ReportGenerator()
    report_data = rg.generate_comprehensive_report()
    print("Report generation complete.")


if __name__ == "__main__":
    sys.exit(main())
