#!/usr/bin/env python3
"""
Test Execution and Comparison Engine.
Executes generated tests on both Sybase and PostgreSQL and compares results.
"""

import asyncio
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import psycopg2
import pymssql
from psycopg2.extras import RealDictCursor

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from config import *

# Setup logging
logging.basicConfig(**LOGGING_CONFIG)
logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Base class for database connections."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connection = None
    
    def connect(self):
        """Connect to database."""
        raise NotImplementedError
    
    def disconnect(self):
        """Disconnect from database."""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute query and return results."""
        raise NotImplementedError
    
    def execute_script(self, script: str) -> Dict[str, Any]:
        """Execute script and return execution results."""
        raise NotImplementedError


class SybaseConnection(DatabaseConnection):
    """Sybase database connection."""
    
    def connect(self):
        """Connect to Sybase database."""
        try:
            self.connection = pymssql.connect(
                server=self.config["server"],
                user=self.config["username"],
                password=self.config["password"],
                database=self.config["database"],
                port=self.config["port"],
                timeout=self.config["timeout"],
                as_dict=True
            )
            logger.info("Connected to Sybase database")
        except Exception as e:
            logger.error(f"Failed to connect to Sybase: {str(e)}")
            raise
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute query on Sybase."""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            
            if cursor.description:
                results = cursor.fetchall()
                return [dict(row) for row in results]
            else:
                return []
                
        except Exception as e:
            logger.error(f"Sybase query execution failed: {str(e)}")
            raise
        finally:
            cursor.close()
    
    def execute_script(self, script: str) -> Dict[str, Any]:
        """Execute test script on Sybase."""
        start_time = time.time()
        results = {
            "success": False,
            "execution_time": 0.0,
            "output": [],
            "errors": [],
            "row_count": 0
        }
        
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            
            # Split script into individual statements
            statements = self._split_sql_statements(script)
            
            for stmt in statements:
                if stmt.strip():
                    try:
                        cursor.execute(stmt)
                        
                        # Capture results if available
                        if cursor.description:
                            rows = cursor.fetchall()
                            results["output"].extend([dict(row) for row in rows])
                            results["row_count"] += len(rows)
                        
                        # Commit after each statement
                        self.connection.commit()
                        
                    except Exception as stmt_error:
                        results["errors"].append({
                            "statement": stmt[:100] + "..." if len(stmt) > 100 else stmt,
                            "error": str(stmt_error)
                        })
                        self.connection.rollback()
            
            results["success"] = len(results["errors"]) == 0
            results["execution_time"] = time.time() - start_time
            
        except Exception as e:
            results["errors"].append({"general_error": str(e)})
            logger.error(f"Sybase script execution failed: {str(e)}")
        finally:
            cursor.close()
        
        return results
    
    def _split_sql_statements(self, script: str) -> List[str]:
        """Split SQL script into individual statements."""
        # Simple statement splitting - can be enhanced for complex cases
        statements = []
        current_stmt = ""
        
        for line in script.split('\n'):
            line = line.strip()
            
            # Skip comments
            if line.startswith('--') or not line:
                continue
            
            current_stmt += line + " "
            
            # Statement ends with semicolon
            if line.endswith(';'):
                statements.append(current_stmt.strip())
                current_stmt = ""
        
        if current_stmt.strip():
            statements.append(current_stmt.strip())
        
        return statements


class PostgreSQLConnection(DatabaseConnection):
    """PostgreSQL database connection."""
    
    def connect(self):
        """Connect to PostgreSQL database."""
        try:
            self.connection = psycopg2.connect(
                host=self.config["host"],
                port=self.config["port"],
                database=self.config["database"],
                user=self.config["username"],
                password=self.config["password"],
                connect_timeout=self.config["timeout"]
            )
            self.connection.autocommit = True
            logger.info("Connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
            raise
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute query on PostgreSQL."""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query)
            
            if cursor.description:
                results = cursor.fetchall()
                return [dict(row) for row in results]
            else:
                return []
                
        except Exception as e:
            logger.error(f"PostgreSQL query execution failed: {str(e)}")
            raise
        finally:
            cursor.close()
    
    def execute_script(self, script: str) -> Dict[str, Any]:
        """Execute test script on PostgreSQL."""
        start_time = time.time()
        results = {
            "success": False,
            "execution_time": 0.0,
            "output": [],
            "errors": [],
            "row_count": 0,
            "notices": []
        }
        
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            
            # Execute the entire script (PostgreSQL handles DO blocks well)
            cursor.execute(script)
            
            # Capture any results
            try:
                if cursor.description:
                    rows = cursor.fetchall()
                    results["output"].extend([dict(row) for row in rows])
                    results["row_count"] += len(rows)
            except psycopg2.ProgrammingError:
                # No results to fetch
                pass
            
            # Capture notices (RAISE NOTICE output)
            for notice in self.connection.notices:
                results["notices"].append(notice.strip())
            
            # Clear notices for next execution
            self.connection.notices.clear()
            
            results["success"] = True
            results["execution_time"] = time.time() - start_time
            
        except Exception as e:
            results["errors"].append({"general_error": str(e)})
            logger.error(f"PostgreSQL script execution failed: {str(e)}")
        finally:
            cursor.close()
        
        return results


class TestExecutor:
    """Executes and compares test results between databases."""
    
    def __init__(self):
        self.sybase_conn = SybaseConnection(DATABASE_CONFIGS["sybase"])
        self.postgres_conn = PostgreSQLConnection(DATABASE_CONFIGS["postgres"])
        self.execution_results = {}
    
    def execute_all_tests(self) -> Dict[str, Any]:
        """Execute all generated test scripts and compare results."""
        
        results = {
            "execution_summary": {
                "total_tests": 0,
                "successful_tests": 0,
                "failed_tests": 0,
                "comparison_results": {}
            },
            "test_results": {},
            "performance_metrics": {},
            "data_comparison": {},
            "issues_found": []
        }
        
        try:
            # Find test files
            test_dir = PROJECT_ROOT / "tests"
            sybase_test_dir = test_dir / "sybase"
            postgres_test_dir = test_dir / "postgres"
            
            if not sybase_test_dir.exists() or not postgres_test_dir.exists():
                logger.error("Test directories not found. Run test generation first.")
                return results
            
            # Get list of test files
            sybase_tests = list(sybase_test_dir.glob("*.sql"))
            postgres_tests = list(postgres_test_dir.glob("*.sql"))
            
            logger.info(f"Found {len(sybase_tests)} Sybase tests and {len(postgres_tests)} PostgreSQL tests")
            
            # Execute tests
            if TEST_EXECUTION["parallel_execution"]:
                results = self._execute_tests_parallel(sybase_tests, postgres_tests, results)
            else:
                results = self._execute_tests_sequential(sybase_tests, postgres_tests, results)
            
            # Compare results
            results = self._compare_test_results(results)
            
            # Generate performance analysis
            results = self._analyze_performance(results)
            
            # Identify issues
            results = self._identify_issues(results)
            
            logger.info(f"Test execution completed. {results['execution_summary']['successful_tests']}/{results['execution_summary']['total_tests']} tests passed")
            
        except Exception as e:
            logger.error(f"Test execution failed: {str(e)}")
            results["execution_error"] = str(e)
        
        return results
    
    def _execute_tests_sequential(self, sybase_tests: List[Path], postgres_tests: List[Path], results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tests sequentially."""
        
        # Match test files by procedure name
        test_pairs = self._match_test_files(sybase_tests, postgres_tests)
        
        results["execution_summary"]["total_tests"] = len(test_pairs)
        
        for proc_name, (sybase_file, postgres_file) in test_pairs.items():
            logger.info(f"Executing tests for procedure: {proc_name}")
            
            test_result = {
                "procedure_name": proc_name,
                "sybase_result": None,
                "postgres_result": None,
                "comparison": None
            }
            
            # Execute Sybase test
            if sybase_file:
                try:
                    with open(sybase_file, 'r', encoding='utf-8') as f:
                        sybase_script = f.read()
                    
                    test_result["sybase_result"] = self.sybase_conn.execute_script(sybase_script)
                    logger.info(f"Sybase test completed for {proc_name}")
                    
                except Exception as e:
                    logger.error(f"Sybase test failed for {proc_name}: {str(e)}")
                    test_result["sybase_result"] = {
                        "success": False,
                        "errors": [{"execution_error": str(e)}]
                    }
            
            # Execute PostgreSQL test
            if postgres_file:
                try:
                    with open(postgres_file, 'r', encoding='utf-8') as f:
                        postgres_script = f.read()
                    
                    test_result["postgres_result"] = self.postgres_conn.execute_script(postgres_script)
                    logger.info(f"PostgreSQL test completed for {proc_name}")
                    
                except Exception as e:
                    logger.error(f"PostgreSQL test failed for {proc_name}: {str(e)}")
                    test_result["postgres_result"] = {
                        "success": False,
                        "errors": [{"execution_error": str(e)}]
                    }
            
            results["test_results"][proc_name] = test_result
            
            # Update summary
            if (test_result["sybase_result"] and test_result["sybase_result"]["success"] and
                test_result["postgres_result"] and test_result["postgres_result"]["success"]):
                results["execution_summary"]["successful_tests"] += 1
            else:
                results["execution_summary"]["failed_tests"] += 1
        
        return results
    
    def _execute_tests_parallel(self, sybase_tests: List[Path], postgres_tests: List[Path], results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tests in parallel."""
        
        test_pairs = self._match_test_files(sybase_tests, postgres_tests)
        results["execution_summary"]["total_tests"] = len(test_pairs)
        
        with ThreadPoolExecutor(max_workers=TEST_EXECUTION["max_workers"]) as executor:
            # Submit test execution tasks
            future_to_proc = {}
            
            for proc_name, (sybase_file, postgres_file) in test_pairs.items():
                future = executor.submit(self._execute_test_pair, proc_name, sybase_file, postgres_file)
                future_to_proc[future] = proc_name
            
            # Collect results
            for future in as_completed(future_to_proc):
                proc_name = future_to_proc[future]
                try:
                    test_result = future.result()
                    results["test_results"][proc_name] = test_result
                    
                    # Update summary
                    if (test_result["sybase_result"] and test_result["sybase_result"]["success"] and
                        test_result["postgres_result"] and test_result["postgres_result"]["success"]):
                        results["execution_summary"]["successful_tests"] += 1
                    else:
                        results["execution_summary"]["failed_tests"] += 1
                        
                    logger.info(f"Completed tests for {proc_name}")
                    
                except Exception as e:
                    logger.error(f"Test execution failed for {proc_name}: {str(e)}")
                    results["execution_summary"]["failed_tests"] += 1
        
        return results
    
    def _execute_test_pair(self, proc_name: str, sybase_file: Optional[Path], postgres_file: Optional[Path]) -> Dict[str, Any]:
        """Execute a pair of test files."""
        
        test_result = {
            "procedure_name": proc_name,
            "sybase_result": None,
            "postgres_result": None,
            "comparison": None
        }
        
        # Execute Sybase test
        if sybase_file:
            try:
                with open(sybase_file, 'r', encoding='utf-8') as f:
                    sybase_script = f.read()
                
                # Create new connection for thread safety
                sybase_conn = SybaseConnection(DATABASE_CONFIGS["sybase"])
                test_result["sybase_result"] = sybase_conn.execute_script(sybase_script)
                sybase_conn.disconnect()
                
            except Exception as e:
                test_result["sybase_result"] = {
                    "success": False,
                    "errors": [{"execution_error": str(e)}]
                }
        
        # Execute PostgreSQL test
        if postgres_file:
            try:
                with open(postgres_file, 'r', encoding='utf-8') as f:
                    postgres_script = f.read()
                
                # Create new connection for thread safety
                postgres_conn = PostgreSQLConnection(DATABASE_CONFIGS["postgres"])
                test_result["postgres_result"] = postgres_conn.execute_script(postgres_script)
                postgres_conn.disconnect()
                
            except Exception as e:
                test_result["postgres_result"] = {
                    "success": False,
                    "errors": [{"execution_error": str(e)}]
                }
        
        return test_result
    
    def _match_test_files(self, sybase_tests: List[Path], postgres_tests: List[Path]) -> Dict[str, Tuple[Optional[Path], Optional[Path]]]:
        """Match Sybase and PostgreSQL test files by procedure name."""
        
        test_pairs = {}
        
        # Create mappings
        sybase_map = {f.stem.replace('_test', ''): f for f in sybase_tests}
        postgres_map = {f.stem.replace('_test', ''): f for f in postgres_tests}
        
        # Find all procedure names
        all_procs = set(sybase_map.keys()) | set(postgres_map.keys())
        
        for proc_name in all_procs:
            sybase_file = sybase_map.get(proc_name)
            postgres_file = postgres_map.get(proc_name)
            test_pairs[proc_name] = (sybase_file, postgres_file)
        
        return test_pairs
    
    def _compare_test_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare test results between Sybase and PostgreSQL."""
        
        comparison_summary = {
            "procedures_compared": 0,
            "identical_results": 0,
            "different_results": 0,
            "execution_differences": [],
            "data_differences": []
        }
        
        for proc_name, test_result in results["test_results"].items():
            sybase_result = test_result["sybase_result"]
            postgres_result = test_result["postgres_result"]
            
            if sybase_result and postgres_result:
                comparison_summary["procedures_compared"] += 1
                
                # Compare execution success
                sybase_success = sybase_result.get("success", False)
                postgres_success = postgres_result.get("success", False)
                
                if sybase_success != postgres_success:
                    comparison_summary["execution_differences"].append({
                        "procedure": proc_name,
                        "sybase_success": sybase_success,
                        "postgres_success": postgres_success,
                        "sybase_errors": sybase_result.get("errors", []),
                        "postgres_errors": postgres_result.get("errors", [])
                    })
                
                # Compare output data
                data_comparison = self._compare_output_data(
                    sybase_result.get("output", []),
                    postgres_result.get("output", []),
                    proc_name
                )
                
                test_result["comparison"] = data_comparison
                
                if data_comparison["identical"]:
                    comparison_summary["identical_results"] += 1
                else:
                    comparison_summary["different_results"] += 1
                    comparison_summary["data_differences"].append({
                        "procedure": proc_name,
                        "differences": data_comparison["differences"]
                    })
        
        results["execution_summary"]["comparison_results"] = comparison_summary
        return results
    
    def _compare_output_data(self, sybase_output: List[Dict], postgres_output: List[Dict], proc_name: str) -> Dict[str, Any]:
        """Compare output data between Sybase and PostgreSQL."""
        
        comparison = {
            "identical": False,
            "row_count_match": False,
            "column_count_match": False,
            "data_match": False,
            "differences": [],
            "similarity_score": 0.0
        }
        
        # Compare row counts
        sybase_rows = len(sybase_output)
        postgres_rows = len(postgres_output)
        comparison["row_count_match"] = sybase_rows == postgres_rows
        
        if sybase_rows == 0 and postgres_rows == 0:
            comparison["identical"] = True
            comparison["similarity_score"] = 1.0
            return comparison
        
        # Compare column structure if data exists
        if sybase_output and postgres_output:
            sybase_columns = set(sybase_output[0].keys()) if sybase_output else set()
            postgres_columns = set(postgres_output[0].keys()) if postgres_output else set()
            comparison["column_count_match"] = len(sybase_columns) == len(postgres_columns)
            
            # Find column differences
            missing_in_postgres = sybase_columns - postgres_columns
            extra_in_postgres = postgres_columns - sybase_columns
            
            if missing_in_postgres:
                comparison["differences"].append({
                    "type": "missing_columns_postgres",
                    "columns": list(missing_in_postgres)
                })
            
            if extra_in_postgres:
                comparison["differences"].append({
                    "type": "extra_columns_postgres", 
                    "columns": list(extra_in_postgres)
                })
        
        # Compare data values
        if comparison["row_count_match"] and sybase_output and postgres_output:
            data_differences = []
            matching_rows = 0
            
            for i, (sybase_row, postgres_row) in enumerate(zip(sybase_output, postgres_output)):
                row_matches = True
                row_differences = []
                
                # Compare common columns
                common_columns = set(sybase_row.keys()) & set(postgres_row.keys())
                
                for col in common_columns:
                    sybase_val = sybase_row[col]
                    postgres_val = postgres_row[col]
                    
                    # Normalize values for comparison
                    if not self._values_equal(sybase_val, postgres_val):
                        row_matches = False
                        row_differences.append({
                            "column": col,
                            "sybase_value": sybase_val,
                            "postgres_value": postgres_val
                        })
                
                if row_matches:
                    matching_rows += 1
                elif row_differences:
                    data_differences.append({
                        "row_index": i,
                        "differences": row_differences
                    })
            
            comparison["data_match"] = matching_rows == sybase_rows
            
            if data_differences:
                comparison["differences"].append({
                    "type": "data_value_differences",
                    "row_differences": data_differences
                })
            
            # Calculate similarity score
            if sybase_rows > 0:
                comparison["similarity_score"] = matching_rows / sybase_rows
            else:
                comparison["similarity_score"] = 1.0
        
        # Determine if results are identical
        comparison["identical"] = (
            comparison["row_count_match"] and
            comparison["column_count_match"] and
            comparison["data_match"] and 
            len(comparison["differences"]) == 0
        )
        
        return comparison
    
    def _values_equal(self, val1: Any, val2: Any) -> bool:
        """Compare two values for equality with type tolerance."""
        
        # Handle None/NULL values
        if val1 is None and val2 is None:
            return True
        if val1 is None or val2 is None:
            return False
        
        # Convert to strings for comparison (handles type differences)
        str1 = str(val1).strip()
        str2 = str(val2).strip()
        
        # Handle numeric comparisons
        try:
            float1 = float(str1)
            float2 = float(str2)
            return abs(float1 - float2) < 1e-10  # Small epsilon for floating point
        except (ValueError, TypeError):
            pass
        
        # String comparison (case-insensitive)
        return str1.lower() == str2.lower()
    
    def _analyze_performance(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance metrics from test execution."""
        
        performance = {
            "average_execution_time": {"sybase": 0.0, "postgres": 0.0},
            "total_execution_time": {"sybase": 0.0, "postgres": 0.0},
            "performance_comparison": [],
            "slowest_procedures": {"sybase": [], "postgres": []},
            "fastest_procedures": {"sybase": [], "postgres": []}
        }
        
        sybase_times = []
        postgres_times = []
        procedure_times = []
        
        for proc_name, test_result in results["test_results"].items():
            sybase_result = test_result.get("sybase_result", {})
            postgres_result = test_result.get("postgres_result", {})
            
            sybase_time = sybase_result.get("execution_time", 0.0)
            postgres_time = postgres_result.get("execution_time", 0.0)
            
            if sybase_time > 0:
                sybase_times.append(sybase_time)
                performance["total_execution_time"]["sybase"] += sybase_time
            
            if postgres_time > 0:
                postgres_times.append(postgres_time)
                performance["total_execution_time"]["postgres"] += postgres_time
            
            if sybase_time > 0 and postgres_time > 0:
                procedure_times.append({
                    "procedure": proc_name,
                    "sybase_time": sybase_time,
                    "postgres_time": postgres_time,
                    "time_difference": postgres_time - sybase_time,
                    "performance_ratio": postgres_time / sybase_time if sybase_time > 0 else 0
                })
        
        # Calculate averages
        if sybase_times:
            performance["average_execution_time"]["sybase"] = sum(sybase_times) / len(sybase_times)
        if postgres_times:
            performance["average_execution_time"]["postgres"] = sum(postgres_times) / len(postgres_times)
        
        # Sort procedures by execution time
        if procedure_times:
            performance["performance_comparison"] = sorted(
                procedure_times, 
                key=lambda x: x["time_difference"], 
                reverse=True
            )
            
            # Identify slowest and fastest procedures
            sybase_sorted = sorted(procedure_times, key=lambda x: x["sybase_time"], reverse=True)
            postgres_sorted = sorted(procedure_times, key=lambda x: x["postgres_time"], reverse=True)
            
            performance["slowest_procedures"]["sybase"] = sybase_sorted[:3]
            performance["slowest_procedures"]["postgres"] = postgres_sorted[:3]
            performance["fastest_procedures"]["sybase"] = sybase_sorted[-3:]
            performance["fastest_procedures"]["postgres"] = postgres_sorted[-3:]
        
        results["performance_metrics"] = performance
        return results
    
    def _identify_issues(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Identify issues from test execution and comparison."""
        
        issues = []
        
        # Check for execution failures
        for proc_name, test_result in results["test_results"].items():
            sybase_result = test_result.get("sybase_result", {})
            postgres_result = test_result.get("postgres_result", {})
            
            if not sybase_result.get("success", False):
                issues.append({
                    "type": "sybase_execution_failure",
                    "procedure": proc_name,
                    "severity": "critical",
                    "details": sybase_result.get("errors", [])
                })
            
            if not postgres_result.get("success", False):
                issues.append({
                    "type": "postgres_execution_failure",
                    "procedure": proc_name,
                    "severity": "critical",
                    "details": postgres_result.get("errors", [])
                })
            
            # Check for data differences
            comparison = test_result.get("comparison", {})
            if comparison and not comparison.get("identical", False):
                severity = "critical" if comparison.get("similarity_score", 1.0) < 0.5 else "warning"
                issues.append({
                    "type": "data_mismatch",
                    "procedure": proc_name,
                    "severity": severity,
                    "similarity_score": comparison.get("similarity_score", 0.0),
                    "differences": comparison.get("differences", [])
                })
        
        # Check for performance issues
        performance = results.get("performance_metrics", {})
        for proc_comparison in performance.get("performance_comparison", []):
            # Flag procedures that are significantly slower in PostgreSQL
            if proc_comparison["performance_ratio"] > 2.0:  # More than 2x slower
                issues.append({
                    "type": "performance_degradation",
                    "procedure": proc_comparison["procedure"],
                    "severity": "warning",
                    "postgres_time": proc_comparison["postgres_time"],
                    "sybase_time": proc_comparison["sybase_time"],
                    "performance_ratio": proc_comparison["performance_ratio"]
                })
        
        results["issues_found"] = issues
        return results
    
    def cleanup_connections(self):
        """Cleanup database connections."""
        try:
            self.sybase_conn.disconnect()
            self.postgres_conn.disconnect()
            logger.info("Database connections cleaned up")
        except Exception as e:
            logger.warning(f"Error during connection cleanup: {str(e)}")


def save_execution_results(results: Dict[str, Any]) -> Path:
    """Save test execution results to file."""
    
    REPORTS_DIR.mkdir(exist_ok=True)
    
    # Save detailed results
    results_file = REPORTS_DIR / "test_execution_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    logger.info(f"Test execution results saved to: {results_file}")
    return results_file


def generate_execution_report(results: Dict[str, Any]) -> str:
    """Generate human-readable execution report."""
    
    report = []
    report.append("=" * 80)
    report.append("TEST EXECUTION AND COMPARISON REPORT")
    report.append("=" * 80)
    report.append("")
    
    # Execution Summary
    summary = results["execution_summary"]
    report.append("EXECUTION SUMMARY:")
    report.append(f"  Total Tests: {summary['total_tests']}")
    report.append(f"  Successful Tests: {summary['successful_tests']}")
    report.append(f"  Failed Tests: {summary['failed_tests']}")
    
    if summary['total_tests'] > 0:
        success_rate = (summary['successful_tests'] / summary['total_tests']) * 100
        report.append(f"  Success Rate: {success_rate:.1f}%")
    
    report.append("")
    
    # Comparison Results
    if "comparison_results" in summary:
        comp_results = summary["comparison_results"]
        report.append("COMPARISON RESULTS:")
        report.append(f"  Procedures Compared: {comp_results['procedures_compared']}")
        report.append(f"  Identical Results: {comp_results['identical_results']}")
        report.append(f"  Different Results: {comp_results['different_results']}")
        
        if comp_results['procedures_compared'] > 0:
            match_rate = (comp_results['identical_results'] / comp_results['procedures_compared']) * 100
            report.append(f"  Match Rate: {match_rate:.1f}%")
        
        report.append("")
    
    # Performance Metrics
    if "performance_metrics" in results:
        perf = results["performance_metrics"]
        report.append("PERFORMANCE ANALYSIS:")
        report.append(f"  Average Sybase Execution Time: {perf['average_execution_time']['sybase']:.3f}s")
        report.append(f"  Average PostgreSQL Execution Time: {perf['average_execution_time']['postgres']:.3f}s")
        report.append(f"  Total Sybase Execution Time: {perf['total_execution_time']['sybase']:.3f}s")
        report.append(f"  Total PostgreSQL Execution Time: {perf['total_execution_time']['postgres']:.3f}s")
        report.append("")
        
        # Performance comparison highlights
        if perf["performance_comparison"]:
            report.append("PERFORMANCE HIGHLIGHTS:")
            
            # Slowest procedures
            slowest = perf["performance_comparison"][:3]
            report.append("  Largest Performance Differences:")
            for proc in slowest:
                if proc["time_difference"] > 0:
                    report.append(f"    {proc['procedure']}: PostgreSQL {proc['time_difference']:.3f}s slower")
                else:
                    report.append(f"    {proc['procedure']}: PostgreSQL {abs(proc['time_difference']):.3f}s faster")
            
            report.append("")
    
    # Issues Summary
    if "issues_found" in results:
        issues = results["issues_found"]
        critical_issues = [i for i in issues if i["severity"] == "critical"]
        warning_issues = [i for i in issues if i["severity"] == "warning"]
        
        report.append("ISSUES SUMMARY:")
        report.append(f"  Critical Issues: {len(critical_issues)}")
        report.append(f"  Warnings: {len(warning_issues)}")
        report.append("")
        
        if critical_issues:
            report.append("CRITICAL ISSUES:")
            for issue in critical_issues[:5]:  # Show top 5
                report.append(f"  • {issue['type']}: {issue['procedure']}")
                if issue['type'] == 'data_mismatch':
                    report.append(f"    Similarity Score: {issue.get('similarity_score', 0.0):.2%}")
            report.append("")
        
        if warning_issues:
            report.append("WARNINGS:")
            for issue in warning_issues[:5]:  # Show top 5
                report.append(f"  • {issue['type']}: {issue['procedure']}")
                if issue['type'] == 'performance_degradation':
                    report.append(f"    Performance Ratio: {issue.get('performance_ratio', 1.0):.2f}x")
            report.append("")
    
    # Recommendations
    report.append("RECOMMENDATIONS:")
    
    if results["execution_summary"]["failed_tests"] > 0:
        report.append("  ❌ Review failed test executions and fix implementation issues")
    
    if "issues_found" in results:
        critical_count = len([i for i in results["issues_found"] if i["severity"] == "critical"])
        if critical_count > 0:
            report.append("  ❌ Address critical data mismatches before deployment")
        
        perf_issues = len([i for i in results["issues_found"] if i["type"] == "performance_degradation"])
        if perf_issues > 0:
            report.append("  ⚠️  Investigate performance degradation in PostgreSQL procedures")
    
    if "comparison_results" in results["execution_summary"]:
        comp = results["execution_summary"]["comparison_results"]
        if comp["procedures_compared"] > 0:
            match_rate = (comp["identical_results"] / comp["procedures_compared"]) * 100
            if match_rate >= 95:
                report.append("Excellent transformation quality - results highly consistent")
            elif match_rate >= 80:
                report.append("Good transformation quality - minor differences detected")
            else:
                report.append("Poor transformation quality - significant differences found")
    
    report.append("")
    report.append("=" * 80)
    
    return "\n".join(report)


def main():
    """Main function to execute tests and compare results."""
    executor = None
    
    try:
        logger.info("Starting test execution and comparison...")
        
        # Initialize test executor
        executor = TestExecutor()
        
        # Execute all tests
        results = executor.execute_all_tests()
        
        # Save results
        results_file = save_execution_results(results)
        
        # Generate and display report
        report = generate_execution_report(results)
        print(report)
        
        # Save report
        report_file = REPORTS_DIR / "test_execution_report.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"Test execution report saved to: {report_file}")
        
        # Determine exit code based on results
        critical_issues = len([i for i in results.get("issues_found", []) if i["severity"] == "critical"])
        failed_tests = results["execution_summary"]["failed_tests"]
        
        if critical_issues > 0 or failed_tests > 0:
            logger.warning("Test execution completed with issues")
            return 1
        else:
            logger.info("Test execution completed successfully")
            return 0
            
    except Exception as e:
        logger.error(f"Test execution failed: {str(e)}")
        return 1
    
    finally:
        if executor:
            executor.cleanup_connections()


if __name__ == "__main__":
    sys.exit(main())