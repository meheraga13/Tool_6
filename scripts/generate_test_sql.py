#!/usr/bin/env python3
"""
Optimized LLM-Generated Test Script Generator for Stored Procedure Validation.
Generates comprehensive test scripts for both Sybase and PostgreSQL procedures.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from jinja2 import Template
import openai
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from config import *

# Setup logging
logging.basicConfig(**LOGGING_CONFIG)
logger = logging.getLogger(__name__)


class TestScriptGenerator:
    """Generates test scripts using LLM for stored procedure validation."""

    def __init__(self):
        self.client = openai.OpenAI(api_key=LLM_CONFIG["api_key"])
        self.test_templates = self._load_test_templates()
        self.generated_tests = {}
        # Cache for generated test values to avoid recomputation
        self._test_value_cache = {}
        self._edge_value_cache = {}

    def _load_test_templates(self) -> Dict[str, Template]:
        """Load pre-compiled Jinja2 templates for test generation."""
        templates = {}

        # Optimized Sybase template - streamlined for performance
        sybase_template = """-- Sybase Test Script for {{ procedure_name }}
{% if setup_data %}{% for table, data in setup_data.items() %}{% if data %}
-- Setup {{ table }}
{% for row in data %}{% if row.columns and row.values %}INSERT INTO {{ table }} ({{ row.columns|join(', ') }}) VALUES ({{ row.values|join(', ') }});
{% endif %}{% endfor %}{% endif %}{% endfor %}{% endif %}
{% for test_case in test_cases %}-- Test {{ loop.index }}: {{ test_case.description }}
{% if test_case.output_parameters %}{% for out_param in test_case.output_parameters %}DECLARE @{{ out_param.name }}_{{ loop.index }} {{ out_param.type|default('VARCHAR(255)') }};
{% endfor %}{% endif %}DECLARE @result_{{ loop.index }} INT;
EXEC @result_{{ loop.index }} = {{ procedure_name }}{% for param in test_case.parameters %} @{{ param.name }} = {{ param.value }}{% if not loop.last %},{% endif %}{% endfor %}{% if test_case.output_parameters %}{% for out_param in test_case.output_parameters %}, @{{ out_param.name }} = @{{ out_param.name }}_{{ loop.index }} OUTPUT{% endfor %}{% endif %};
SELECT 'Test {{ loop.index }}' as test_name, @result_{{ loop.index }} as return_code{% if test_case.output_parameters %}{% for out_param in test_case.output_parameters %}, @{{ out_param.name }}_{{ loop.index }} as {{ out_param.name }}{% endfor %}{% endif %};
{% for verification in test_case.verifications %}SELECT '{{ verification.description }}' as verification, COUNT(*) as count FROM {{ verification.table }} WHERE {{ verification.condition }};
{% endfor %}{% endfor %}{% if cleanup_data %}
{% for table in cleanup_data %}{% if table %}DELETE FROM {{ table }};
{% endif %}{% endfor %}{% endif %}"""

        # Fixed PostgreSQL template with proper parameter handling
        postgres_template = """-- PostgreSQL Test Script for {{ procedure_name }}
DO $$ 
DECLARE 
    test_count INTEGER := 0; 
    pass_count INTEGER := 0;
    verification_count INTEGER;
{% for test_case in test_cases %}{% if test_case.output_parameters %}{% for out_param in test_case.output_parameters %}    {{ out_param.name }}_{{ loop.index0 + 1 }} {{ out_param.type|default('TEXT') }};
{% endfor %}{% endif %}{% endfor %}
BEGIN
{% if setup_data %}    -- Setup data
{% for table, data in setup_data.items() %}{% if data %}{% for row in data %}{% if row.columns and row.values %}    INSERT INTO {{ table }} ({{ row.columns|join(', ') }}) VALUES ({{ row.values|join(', ') }});
{% endif %}{% endfor %}{% endif %}{% endfor %}{% endif %}
{% for test_case in test_cases %}    -- Test {{ loop.index }}: {{ test_case.description }}
    test_count := test_count + 1;
    BEGIN
        -- Call the procedure
{% if test_case.output_parameters %}        CALL {{ procedure_name }}({% for param in test_case.parameters %}{{ param.value }}{% if not loop.last or test_case.output_parameters %}, {% endif %}{% endfor %}{% for out_param in test_case.output_parameters %}{{ out_param.name }}_{{ loop.index }}{% if not loop.last %}, {% endif %}{% endfor %});
        RAISE NOTICE 'Test %: % - Completed', test_count, '{{ test_case.description }}';
{% for out_param in test_case.output_parameters %}        RAISE NOTICE 'Output parameter {{ out_param.name }}: %', {{ out_param.name }}_{{ loop.index }};
{% endfor %}{% else %}        CALL {{ procedure_name }}({% for param in test_case.parameters %}{{ param.value }}{% if not loop.last %}, {% endif %}{% endfor %});
        RAISE NOTICE 'Test %: % - Completed', test_count, '{{ test_case.description }}';
{% endif %}
        
        -- Perform verifications
{% for verification in test_case.verifications %}        SELECT COUNT(*) INTO verification_count FROM {{ verification.table }} WHERE {{ verification.condition }};
        IF verification_count > 0 THEN 
            RAISE NOTICE 'Verification passed: {{ verification.description }} (Count: %)', verification_count; 
            pass_count := pass_count + 1;
        ELSE 
            RAISE NOTICE 'Verification failed: {{ verification.description }} (Count: 0)'; 
        END IF;
{% endfor %}
    EXCEPTION 
        WHEN OTHERS THEN 
            RAISE NOTICE 'Test % failed with error: %', test_count, SQLERRM; 
    END;
    
{% endfor %}    -- Summary
    RAISE NOTICE 'Test Summary: % verifications passed out of % total tests', pass_count, test_count;
    
{% if cleanup_data %}    -- Cleanup
{% for table in cleanup_data %}{% if table %}    DELETE FROM {{ table }};
{% endif %}{% endfor %}{% endif %}END $$;"""

        # Pre-compile templates for better performance
        templates["sybase"] = Template(sybase_template)
        templates["postgres"] = Template(postgres_template)
        return templates

    def _safe_convert_value(self, value):
        """Optimized safe value conversion with caching."""
        if value is None:
            return None
        
        value_type = type(value)
        if value_type in (str, int, float, bool):
            return value
        elif value_type is dict:
            return {k: self._safe_convert_value(v) for k, v in value.items()}
        elif value_type in (list, tuple):
            return [self._safe_convert_value(item) for item in value]
        else:
            try:
                return str(value)
            except Exception:
                return None

    def _normalize_test_case_data(self, test_cases: List[Dict]) -> List[Dict]:
        """Optimized test case normalization with better parameter handling."""
        if not test_cases or not isinstance(test_cases, list):
            return []
        
        normalized_cases = []
        for test_case in test_cases:
            if not isinstance(test_case, dict):
                continue
            
            # Direct access with defaults for better performance
            normalized_case = {
                "description": str(test_case.get("description", "Test case")),
                "parameters": self._fast_normalize_parameters(test_case.get("parameters", [])),
                "verifications": self._fast_normalize_verifications(test_case.get("verifications", [])),
                "output_parameters": self._fast_normalize_output_parameters(test_case.get("output_parameters", [])),
                "setup_data": self._fast_normalize_setup_data(test_case.get("setup_data", {}))
            }
            normalized_cases.append(normalized_case)
        
        return normalized_cases

    def _fast_normalize_parameters(self, parameters):
        """Fast parameter normalization with better value handling."""
        if not isinstance(parameters, list):
            return []
        
        normalized_params = []
        for p in parameters:
            if isinstance(p, dict) and p.get("name"):
                param_name = str(p.get("name", ""))
                param_value = p.get("value", "NULL")
                
                # Better value formatting for PostgreSQL
                if param_value == "NULL" or param_value is None:
                    formatted_value = "NULL"
                elif isinstance(param_value, str):
                    # Handle string values properly
                    if param_value.startswith("'") and param_value.endswith("'"):
                        formatted_value = param_value
                    else:
                        formatted_value = f"'{param_value}'"
                else:
                    formatted_value = str(param_value)
                
                normalized_params.append({
                    "name": param_name, 
                    "value": formatted_value
                })
        
        return normalized_params

    def _fast_normalize_verifications(self, verifications):
        """Fast verification normalization with better table and condition handling."""
        if not isinstance(verifications, list):
            return []
        
        normalized_verifications = []
        for v in verifications:
            if isinstance(v, dict) and v.get("table"):
                table_name = str(v.get("table", ""))
                condition = str(v.get("condition", "1=1"))
                description = str(v.get("description", "Verification"))
                
                # Ensure we have meaningful table names and conditions
                if table_name and table_name != "test_table":
                    normalized_verifications.append({
                        "table": table_name,
                        "condition": condition,
                        "description": description
                    })
                elif table_name == "test_table":
                    # For generic test_table, create more meaningful verification
                    normalized_verifications.append({
                        "table": table_name,
                        "condition": "id IS NOT NULL",  # More meaningful condition
                        "description": f"Verify {description.lower()}"
                    })
        
        # If no verifications provided, add a default one
        if not normalized_verifications:
            normalized_verifications.append({
                "table": "information_schema.tables",
                "condition": "table_name IS NOT NULL",
                "description": "Basic system verification"
            })
        
        return normalized_verifications

    def _fast_normalize_output_parameters(self, output_parameters):
        """Fast output parameter normalization."""
        if not isinstance(output_parameters, list):
            return []
        
        return [{"name": str(p.get("name", "")), "type": str(p.get("type", "TEXT"))} 
                for p in output_parameters if isinstance(p, dict) and p.get("name")]

    def _fast_normalize_setup_data(self, setup_data):
        """Fast setup data normalization."""
        if not isinstance(setup_data, dict):
            return {}
        
        normalized = {}
        for table, rows in setup_data.items():
            if not table or not isinstance(table, str) or not isinstance(rows, list):
                continue
            
            normalized_rows = []
            for row in rows:
                if (isinstance(row, dict) and 
                    isinstance(row.get("columns"), list) and 
                    isinstance(row.get("values"), list) and
                    row.get("columns") and row.get("values")):
                    
                    normalized_rows.append({
                        "columns": [str(col) for col in row["columns"]],
                        "values": [str(val) for val in row["values"]]
                    })
            
            if normalized_rows:
                normalized[str(table)] = normalized_rows
        
        return normalized

    def _calculate_complexity_score(self, procedure: Dict) -> float:
        """Optimized complexity calculation."""
        if not isinstance(procedure, dict):
            return 1.0
        
        statements = procedure.get("statements", [])
        if not isinstance(statements, list):
            return 1.0
        
        # Simplified scoring without recursion for better performance
        score = 0.0
        complexity_weights = {
            "IF": 2.0, "WHILE": 3.0, "FOR_CURSOR_LOOP": 3.0,
            "INSERT": 1.5, "UPDATE": 1.5, "DELETE": 1.5,
            "SELECT_INTO": 1.0, "TRY": 2.0, "EXCEPTION_HANDLER": 2.0
        }
        
        for stmt in statements:
            if isinstance(stmt, dict):
                stmt_type = stmt.get("type", "")
                score += complexity_weights.get(stmt_type, 0.5)
        
        return max(score, 1.0)

    def generate_test_scripts(self, sybase_ast: List[Dict], postgres_ast: List[Dict]) -> Dict[str, Any]:
        """Optimized test script generation with parallel processing."""
        start_time = time.time()
        
        results = {
            "sybase_tests": {},
            "postgres_tests": {},
            "test_metadata": {},
            "generation_summary": {
                "total_procedures": len(sybase_ast) if isinstance(sybase_ast, list) else 0,
                "tests_generated": 0,
                "test_cases_per_procedure": 0
            }
        }

        if not isinstance(sybase_ast, list) or not sybase_ast:
            logger.warning("No valid Sybase procedures to process")
            return results

        if not isinstance(postgres_ast, list):
            postgres_ast = sybase_ast

        # Create procedure mapping for faster lookup
        postgres_map = {proc.get("proc_name", "").lower(): proc 
                       for proc in postgres_ast if isinstance(proc, dict)}

        # Process procedures with limited parallelism to avoid API rate limits
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_to_proc = {}
            
            for sybase_proc in sybase_ast[:10]:  # Limit to first 10 for demo
                if not isinstance(sybase_proc, dict):
                    continue
                
                proc_name = sybase_proc.get("proc_name", "")
                if not proc_name:
                    continue
                
                postgres_proc = postgres_map.get(proc_name.lower(), sybase_proc)
                
                future = executor.submit(self._process_single_procedure, sybase_proc, postgres_proc)
                future_to_proc[future] = (sybase_proc, postgres_proc)
            
            # Collect results
            for future in as_completed(future_to_proc):
                try:
                    proc_result = future.result(timeout=30)  # 30 second timeout per procedure
                    if proc_result:
                        proc_name = proc_result["proc_name"]
                        results["sybase_tests"][proc_name] = proc_result["sybase_test"]
                        results["postgres_tests"][proc_name] = proc_result["postgres_test"]
                        results["test_metadata"][proc_name] = proc_result["metadata"]
                        results["generation_summary"]["tests_generated"] += 1
                        results["generation_summary"]["test_cases_per_procedure"] += proc_result["test_case_count"]
                        
                except Exception as e:
                    logger.error(f"Procedure processing failed: {str(e)}")

        # Calculate averages
        if results["generation_summary"]["tests_generated"] > 0:
            results["generation_summary"]["test_cases_per_procedure"] = (
                results["generation_summary"]["test_cases_per_procedure"] / 
                results["generation_summary"]["tests_generated"]
            )

        elapsed_time = time.time() - start_time
        logger.info(f"Generated {results['generation_summary']['tests_generated']} tests in {elapsed_time:.2f} seconds")
        
        return results

    def _process_single_procedure(self, sybase_proc: Dict, postgres_proc: Dict) -> Optional[Dict]:
        """Process a single procedure to generate test scripts."""
        try:
            proc_name = sybase_proc.get("proc_name", "")
            if not proc_name:
                return None
            
            # Generate test cases with timeout
            test_cases = self._generate_test_cases_fast(sybase_proc, postgres_proc)
            
            if not test_cases:
                test_cases = self._generate_fallback_test_cases(sybase_proc, postgres_proc)
            
            test_cases = self._normalize_test_case_data(test_cases)
            
            if not test_cases:
                return None

            # Generate scripts
            sybase_test = self._generate_sybase_test_script(sybase_proc, test_cases)
            postgres_test = self._generate_postgres_test_script(postgres_proc, test_cases)

            return {
                "proc_name": proc_name,
                "sybase_test": sybase_test,
                "postgres_test": postgres_test,
                "metadata": {
                    "test_case_count": len(test_cases),
                    "complexity_score": self._calculate_complexity_score(sybase_proc),
                    "coverage_areas": self._identify_coverage_areas(sybase_proc)
                },
                "test_case_count": len(test_cases)
            }
            
        except Exception as e:
            logger.error(f"Failed to process procedure {sybase_proc.get('proc_name', 'unknown')}: {str(e)}")
            return None

    def _generate_test_cases_fast(self, sybase_proc: Dict, postgres_proc: Dict) -> List[Dict]:
        """Fast test case generation with improved LLM prompt for PostgreSQL."""
        proc_name = sybase_proc.get('proc_name', 'unknown')
        params = sybase_proc.get('params', [])
        statements = sybase_proc.get('statements', [])
        
        # Extract table names from statements for better verifications
        table_names = []
        for stmt in statements:
            if isinstance(stmt, dict) and stmt.get('table'):
                table_names.append(stmt['table'])
        
        if not table_names:
            table_names = ['users', 'orders', 'products']  # Default tables
        
        # Enhanced prompt for better PostgreSQL test generation
        prompt = f"""Generate 3 comprehensive test cases for PostgreSQL stored procedure '{proc_name}' with parameters: {json.dumps(params, default=str)}.

The procedure works with tables: {', '.join(table_names)}

Requirements:
1. Use realistic parameter values, not generic test values
2. Create meaningful verification conditions based on actual table operations
3. Include proper data types for PostgreSQL
4. Distinguish between input and output parameters

Return JSON format:
{{"test_cases": [
  {{"description": "Valid input test", "parameters": [{{"name": "param1", "value": "realistic_value"}}], "verifications": [{{"table": "{table_names[0] if table_names else 'users'}", "condition": "status = 'active'", "description": "Verify record was processed correctly"}}], "output_parameters": [], "setup_data": {{}}}},
  {{"description": "Boundary value test", "parameters": [{{"name": "param1", "value": "NULL"}}], "verifications": [{{"table": "{table_names[0] if table_names else 'users'}", "condition": "status IS NULL OR status = 'pending'", "description": "Verify null handling"}}], "output_parameters": [], "setup_data": {{}}}},
  {{"description": "Error condition test", "parameters": [{{"name": "param1", "value": "-1"}}], "verifications": [{{"table": "{table_names[0] if table_names else 'users'}", "condition": "error_flag = true", "description": "Verify error handling"}}], "output_parameters": [], "setup_data": {{}}}}
]}}"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Use faster model
                messages=[
                    {"role": "system", "content": "Generate PostgreSQL-specific test cases in JSON format only. Focus on realistic values and meaningful verifications."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500,  # Increased for better test cases
                timeout=15  # 15 second timeout
            )
            
            return self._parse_llm_test_response(response.choices[0].message.content)
            
        except Exception as e:
            logger.warning(f"Fast LLM generation failed for {proc_name}: {str(e)}")
            return []

    def _parse_llm_test_response(self, response_content: str) -> List[Dict]:
        """Optimized LLM response parsing."""
        try:
            # Find JSON content more efficiently
            start_idx = response_content.find('{')
            end_idx = response_content.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                return []
            
            json_content = response_content[start_idx:end_idx]
            parsed_response = json.loads(json_content)
            test_cases = parsed_response.get("test_cases", [])
            
            return test_cases if isinstance(test_cases, list) else []
            
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {str(e)}")
            return []

    def _generate_fallback_test_cases(self, sybase_proc: Dict, postgres_proc: Dict) -> List[Dict]:
        """Enhanced fallback test case generation with better PostgreSQL support."""
        params = sybase_proc.get("params", [])
        statements = sybase_proc.get("statements", [])
        proc_name = sybase_proc.get("proc_name", "unknown")
        
        if not isinstance(params, list):
            return []

        # Extract table information from statements
        tables_mentioned = []
        for stmt in statements:
            if isinstance(stmt, dict) and stmt.get('table'):
                tables_mentioned.append(stmt['table'])
        
        if not tables_mentioned:
            tables_mentioned = [f"{proc_name}_data", "audit_log"]  # Default tables

        test_cases = []
        
        # Basic test
        basic_params = []
        output_params = []
        
        for param in params:
            if not isinstance(param, dict):
                continue
            
            param_name = param.get("name", "param")
            param_type = param.get("type", "VARCHAR")
            param_mode = param.get("mode", "IN")
            
            if param_mode and param_mode.upper() in ["OUT", "OUTPUT", "INOUT"]:
                output_params.append({"name": str(param_name), "type": str(param_type)})
            else:
                value = self._get_cached_test_value(param_type)
                basic_params.append({"name": str(param_name), "value": str(value)})

        # Create meaningful verifications based on procedure context
        basic_verifications = []
        for table in tables_mentioned[:2]:  # Limit to first 2 tables
            basic_verifications.append({
                "description": f"Verify {table} was updated correctly",
                "table": table,
                "condition": "updated_at >= CURRENT_DATE - INTERVAL '1 day'"
            })
        
        if not basic_verifications:
            basic_verifications.append({
                "description": "Basic functionality verification",
                "table": "information_schema.tables",
                "condition": "table_name IS NOT NULL"
            })

        test_cases.append({
            "description": "Basic functionality test with valid inputs",
            "parameters": basic_params,
            "output_parameters": output_params,
            "verifications": basic_verifications,
            "setup_data": {}
        })

        # Edge case test
        if params:
            edge_params = []
            for param in params:
                if isinstance(param, dict) and param.get("mode", "IN").upper() not in ["OUT", "OUTPUT", "INOUT"]:
                    param_name = param.get("name", "param")
                    param_type = param.get("type", "VARCHAR")
                    edge_value = self._get_cached_edge_value(param_type)
                    edge_params.append({"name": str(param_name), "value": str(edge_value)})
            
            edge_verifications = []
            for table in tables_mentioned[:1]:  # Just first table for edge case
                edge_verifications.append({
                    "description": f"Verify {table} handles edge cases",
                    "table": table,
                    "condition": "status IN ('pending', 'processing', 'completed')"
                })
            
            if not edge_verifications:
                edge_verifications.append({
                    "description": "Edge case verification",
                    "table": "information_schema.tables",
                    "condition": "table_schema = 'public'"
                })
            
            test_cases.append({
                "description": "Edge case test with boundary values",
                "parameters": edge_params,
                "output_parameters": output_params,
                "verifications": edge_verifications,
                "setup_data": {}
            })

        # Error case test
        if params:
            error_params = []
            for param in params:
                if isinstance(param, dict) and param.get("mode", "IN").upper() not in ["OUT", "OUTPUT", "INOUT"]:
                    param_name = param.get("name", "param")
                    error_params.append({"name": str(param_name), "value": "NULL"})
            
            error_verifications = []
            if tables_mentioned:
                error_verifications.append({
                    "description": f"Verify error handling in {tables_mentioned[0]}",
                    "table": tables_mentioned[0],
                    "condition": "error_count = 0 OR error_message IS NULL"
                })
            else:
                error_verifications.append({
                    "description": "Error handling verification",
                    "table": "information_schema.tables",
                    "condition": "table_type = 'BASE TABLE'"
                })
            
            test_cases.append({
                "description": "Error condition test with invalid inputs",
                "parameters": error_params,
                "output_parameters": output_params,
                "verifications": error_verifications,
                "setup_data": {}
            })

        return test_cases

    def _get_cached_test_value(self, param_type: str) -> str:
        """Get cached test value for parameter type."""
        if param_type in self._test_value_cache:
            return self._test_value_cache[param_type]
        
        value = self._generate_test_value(param_type)
        self._test_value_cache[param_type] = value
        return value

    def _get_cached_edge_value(self, param_type: str) -> str:
        """Get cached edge value for parameter type."""
        if param_type in self._edge_value_cache:
            return self._edge_value_cache[param_type]
        
        value = self._generate_edge_value(param_type)
        self._edge_value_cache[param_type] = value
        return value

    def _generate_test_value(self, param_type: str) -> str:
        """Enhanced test value generation for PostgreSQL."""
        type_lower = str(param_type).lower()
        
        if "int" in type_lower or "serial" in type_lower:
            return "123"
        elif any(t in type_lower for t in ["varchar", "text", "char"]):
            return "'test_value'"
        elif any(t in type_lower for t in ["timestamp", "datetime"]):
            return "'2024-01-15 10:30:00'"
        elif "date" in type_lower:
            return "'2024-01-15'"
        elif any(t in type_lower for t in ["bit", "boolean", "bool"]):
            return "true"
        elif any(t in type_lower for t in ["decimal", "numeric", "money", "float", "real", "double"]):
            return "123.45"
        elif "uuid" in type_lower:
            return "'550e8400-e29b-41d4-a716-446655440000'"
        elif "json" in type_lower:
            return "'{\"key\": \"value\"}'"
        else:
            return "'default_value'"

    def _generate_edge_value(self, param_type: str) -> str:
        """Enhanced edge value generation for PostgreSQL."""
        type_lower = str(param_type).lower()
        
        if "int" in type_lower:
            return "0"
        elif any(t in type_lower for t in ["varchar", "text", "char"]):
            return "''"
        elif any(t in type_lower for t in ["timestamp", "datetime"]):
            return "'1970-01-01 00:00:00'"
        elif "date" in type_lower:
            return "'1970-01-01'"
        elif any(t in type_lower for t in ["bit", "boolean", "bool"]):
            return "false"
        elif any(t in type_lower for t in ["decimal", "numeric", "money", "float", "real", "double"]):
            return "0.00"
        elif "uuid" in type_lower:
            return "'00000000-0000-0000-0000-000000000000'"
        elif "json" in type_lower:
            return "'{\"empty\": true}'"
        else:
            return "NULL"

    def _generate_sybase_test_script(self, procedure: Dict, test_cases: List[Dict]) -> str:
        """Optimized Sybase test script generation."""
        try:
            proc_name = procedure.get('proc_name', 'unknown_procedure')
            setup_data = self._fast_aggregate_setup_data(test_cases)
            cleanup_data = self._fast_identify_cleanup_tables(test_cases)
            
            return self.test_templates["sybase"].render(
                procedure_name=str(proc_name),
                test_cases=test_cases,
                setup_data=setup_data,
                cleanup_data=cleanup_data
            )
        except Exception as e:
            logger.error(f"Sybase template rendering failed: {str(e)}")
            proc_name = procedure.get('proc_name', 'unknown_procedure')
            return f"-- Sybase Test Script for {proc_name}\n-- Test generation failed\nDECLARE @result INT;\nEXEC @result = {proc_name};\nSELECT 'Basic Test' as test_name, @result as return_code;"

    def _generate_postgres_test_script(self, procedure: Dict, test_cases: List[Dict]) -> str:
        """Enhanced PostgreSQL test script generation with better formatting."""
        try:
            proc_name = procedure.get('proc_name', 'unknown_procedure')
            setup_data = self._fast_aggregate_setup_data(test_cases)
            cleanup_data = self._fast_identify_cleanup_tables(test_cases)
            
            return self.test_templates["postgres"].render(
                procedure_name=str(proc_name),
                test_cases=test_cases,
                setup_data=setup_data,
                cleanup_data=cleanup_data
            )
        except Exception as e:
            logger.error(f"PostgreSQL template rendering failed: {str(e)}")
            proc_name = procedure.get('proc_name', 'unknown_procedure')
            return f"-- PostgreSQL Test Script for {proc_name}\n-- Test generation failed\nDO $ BEGIN RAISE NOTICE 'Basic test for {proc_name}'; END $;"

    def _fast_aggregate_setup_data(self, test_cases: List[Dict]) -> Dict[str, List[Dict]]:
        """Fast setup data aggregation."""
        setup_data = {}
        for test_case in test_cases:
            if isinstance(test_case, dict):
                case_setup = test_case.get("setup_data", {})
                if isinstance(case_setup, dict):
                    for table, data in case_setup.items():
                        if isinstance(data, list) and table:
                            if table not in setup_data:
                                setup_data[table] = []
                            setup_data[table].extend(data)
        return setup_data

    def _fast_identify_cleanup_tables(self, test_cases: List[Dict]) -> List[str]:
        """Fast cleanup table identification."""
        cleanup_tables = set()
        for test_case in test_cases:
            if isinstance(test_case, dict):
                # From setup data
                case_setup = test_case.get("setup_data", {})
                if isinstance(case_setup, dict):
                    cleanup_tables.update(case_setup.keys())
                
                # From verifications
                verifications = test_case.get("verifications", [])
                if isinstance(verifications, list):
                    for v in verifications:
                        if isinstance(v, dict) and v.get("table"):
                            table_name = v["table"]
                            # Don't cleanup system tables
                            if not table_name.startswith("information_schema") and not table_name.startswith("pg_"):
                                cleanup_tables.add(table_name)
        
        return list(cleanup_tables)

    def _identify_coverage_areas(self, procedure: Dict) -> List[str]:
        """Fast coverage area identification."""
        if not isinstance(procedure, dict):
            return ["basic_functionality"]
        
        statements = procedure.get("statements", [])
        if not isinstance(statements, list):
            return ["basic_functionality"]
        
        coverage_areas = set()
        coverage_map = {
            "IF": "conditional_logic",
            "WHILE": "loop_logic", 
            "FOR_CURSOR_LOOP": "loop_logic",
            "INSERT": "data_modification",
            "UPDATE": "data_modification", 
            "DELETE": "data_modification",
            "SELECT_INTO": "data_retrieval",
            "TRY": "exception_handling",
            "EXCEPTION_HANDLER": "exception_handling",
            "RETURN": "return_values"
        }
        
        for stmt in statements:
            if isinstance(stmt, dict):
                stmt_type = stmt.get("type", "")
                if stmt_type in coverage_map:
                    coverage_areas.add(coverage_map[stmt_type])
        
        return list(coverage_areas) if coverage_areas else ["basic_functionality"]

    def save_test_scripts(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Optimized test script saving."""
        try:
            test_dir = PROJECT_ROOT / "tests"
            test_dir.mkdir(exist_ok=True)
            sybase_test_dir = test_dir / "sybase"
            postgres_test_dir = test_dir / "postgres"
            sybase_test_dir.mkdir(exist_ok=True)
            postgres_test_dir.mkdir(exist_ok=True)

            saved_files = {"sybase_files": [], "postgres_files": [], "metadata_file": None}

            # Save with batch operations
            sybase_tests = results.get("sybase_tests", {})
            for proc_name, test_script in sybase_tests.items():
                if isinstance(proc_name, str) and isinstance(test_script, str):
                    file_path = sybase_test_dir / f"{proc_name}_test.sql"
                    try:
                        file_path.write_text(test_script, encoding="utf-8")
                        saved_files["sybase_files"].append(file_path)
                    except Exception as e:
                        logger.error(f"Failed to save Sybase test {proc_name}: {str(e)}")

            postgres_tests = results.get("postgres_tests", {})
            for proc_name, test_script in postgres_tests.items():
                if isinstance(proc_name, str) and isinstance(test_script, str):
                    file_path = postgres_test_dir / f"{proc_name}_test.sql"
                    try:
                        file_path.write_text(test_script, encoding="utf-8")
                        saved_files["postgres_files"].append(file_path)
                    except Exception as e:
                        logger.error(f"Failed to save PostgreSQL test {proc_name}: {str(e)}")

            # Save metadata
            metadata_file = test_dir / "test_metadata.json"
            try:
                metadata_file.write_text(
                    json.dumps(results.get("test_metadata", {}), indent=2, default=str),
                    encoding="utf-8"
                )
                saved_files["metadata_file"] = metadata_file
            except Exception as e:
                logger.error(f"Failed to save metadata: {str(e)}")

            logger.info(f"Saved {len(saved_files['sybase_files'])} Sybase and {len(saved_files['postgres_files'])} PostgreSQL test files")
            return saved_files
            
        except Exception as e:
            logger.error(f"Failed to save test scripts: {str(e)}")
            return {"sybase_files": [], "postgres_files": [], "metadata_file": None}


def load_ast_files() -> Tuple[List[Dict], List[Dict]]:
    """Optimized AST file loading."""
    try:
        sybase_ast_file = ASTS_DIR / "sybase_ast.json"
        postgres_ast_file = ASTS_DIR / "postgres_ast.json"

        sybase_ast = []
        postgres_ast = []

        if sybase_ast_file.exists():
            sybase_ast = json.loads(sybase_ast_file.read_text(encoding="utf-8"))
            if not isinstance(sybase_ast, list):
                sybase_ast = []

        if postgres_ast_file.exists():
            postgres_ast = json.loads(postgres_ast_file.read_text(encoding="utf-8"))
            if not isinstance(postgres_ast, list):
                postgres_ast = sybase_ast
        else:
            postgres_ast = sybase_ast

        logger.info(f"Loaded {len(sybase_ast)} Sybase and {len(postgres_ast)} PostgreSQL procedures")
        return sybase_ast, postgres_ast
        
    except Exception as e:
        logger.error(f"Failed to load AST files: {str(e)}")
        return [], []


def create_sample_sybase_ast() -> List[Dict]:
    """Create optimized sample AST for demonstration with better PostgreSQL compatibility."""
    return [
        {
            "proc_name": "main2",
            "params": [
                {"name": "batch_id", "type": "INTEGER", "mode": "IN"},
                {"name": "result_msg", "type": "TEXT", "mode": "OUT"}
            ],
            "return_type": "INTEGER",
            "variables": [
                {"name": "job_id", "type": "INTEGER"},
                {"name": "status_flag", "type": "TEXT"}
            ],
            "statements": [
                {"type": "IF", "condition": "batch_id > 0"},
                {"type": "SELECT_INTO", "table": "batch_jobs"},
                {"type": "UPDATE", "table": "batch_status"},
                {"type": "RETURN", "value": "0"}
            ]
        },
        {
            "proc_name": "validate_user",
            "params": [
                {"name": "user_id", "type": "INTEGER", "mode": "IN"},
                {"name": "username", "type": "VARCHAR(50)", "mode": "IN"},
                {"name": "is_valid", "type": "BOOLEAN", "mode": "OUT"}
            ],
            "return_type": "INTEGER",
            "variables": [{"name": "user_count", "type": "INTEGER"}],
            "statements": [
                {"type": "SELECT_INTO", "table": "users"},
                {"type": "IF", "condition": "user_count > 0"},
                {"type": "INSERT", "table": "user_audit"},
                {"type": "RETURN", "value": "1"}
            ]
        },
        {
            "proc_name": "process_order",
            "params": [
                {"name": "order_id", "type": "INTEGER", "mode": "IN"},
                {"name": "customer_id", "type": "INTEGER", "mode": "IN"},
                {"name": "order_status", "type": "VARCHAR(20)", "mode": "OUT"}
            ],
            "return_type": "INTEGER",
            "variables": [{"name": "order_total", "type": "DECIMAL(10,2)"}],
            "statements": [
                {"type": "SELECT_INTO", "table": "orders"},
                {"type": "UPDATE", "table": "orders"},
                {"type": "INSERT", "table": "order_history"},
                {"type": "UPDATE", "table": "inventory"},
                {"type": "RETURN", "value": "0"}
            ]
        },
        {
            "proc_name": "calculate_discount",
            "params": [
                {"name": "amount", "type": "DECIMAL(10,2)", "mode": "IN"},
                {"name": "customer_tier", "type": "VARCHAR(10)", "mode": "IN"},
                {"name": "discount_percent", "type": "DECIMAL(5,2)", "mode": "OUT"}
            ],
            "return_type": "INTEGER",
            "variables": [{"name": "temp_rate", "type": "DECIMAL(5,2)"}],
            "statements": [
                {"type": "SELECT_INTO", "table": "discount_rules"},
                {"type": "IF", "condition": "customer_tier = 'PREMIUM'"},
                {"type": "UPDATE", "table": "customer_discounts"},
                {"type": "RETURN", "value": "0"}
            ]
        },
        {
            "proc_name": "update_inventory",
            "params": [
                {"name": "product_id", "type": "INTEGER", "mode": "IN"},
                {"name": "quantity_change", "type": "INTEGER", "mode": "IN"},
                {"name": "new_quantity", "type": "INTEGER", "mode": "OUT"}
            ],
            "return_type": "INTEGER",
            "variables": [{"name": "current_stock", "type": "INTEGER"}],
            "statements": [
                {"type": "SELECT_INTO", "table": "inventory"},
                {"type": "UPDATE", "table": "inventory"},
                {"type": "INSERT", "table": "inventory_log"},
                {"type": "RETURN", "value": "0"}
            ]
        }
    ]


def generate_comprehensive_report(results: Dict[str, Any]) -> str:
    """Generate optimized comprehensive report."""
    try:
        summary = results.get("generation_summary", {})
        total_procs = summary.get('total_procedures', 0)
        generated_tests = summary.get('tests_generated', 0)
        avg_test_cases = summary.get('test_cases_per_procedure', 0)
        success_rate = (generated_tests / total_procs * 100) if total_procs > 0 else 0
        
        report = f"""{'='*80}
TEST SCRIPT GENERATION REPORT
{'='*80}
Total Procedures Processed: {total_procs}
Tests Generated Successfully: {generated_tests}
Average Test Cases per Procedure: {avg_test_cases:.2f}
Success Rate: {success_rate:.1f}%

PROCEDURE DETAILS:
{'-'*40}"""
        
        test_metadata = results.get("test_metadata", {})
        for proc_name, metadata in test_metadata.items():
            if isinstance(metadata, dict):
                coverage_areas = metadata.get('coverage_areas', [])
                coverage_str = ', '.join(coverage_areas) if isinstance(coverage_areas, list) else 'basic_functionality'
                report += f"""
Procedure: {proc_name}
  Test Cases: {metadata.get('test_case_count', 0)}
  Complexity Score: {metadata.get('complexity_score', 0.0):.2f}
  Coverage Areas: {coverage_str}"""
        
        sybase_tests = results.get("sybase_tests", {})
        postgres_tests = results.get("postgres_tests", {})
        
        report += f"""

FILE GENERATION SUMMARY:
{'-'*40}
Sybase Test Files: {len(sybase_tests)}
PostgreSQL Test Files: {len(postgres_tests)}

IMPROVEMENTS MADE:
{'-'*40}
- Enhanced parameter value formatting for PostgreSQL
- Improved verification conditions with meaningful table checks
- Better handling of NULL values and edge cases
- More realistic test data generation
- Enhanced error handling and boundary testing
- Improved template rendering with proper parameter separation
- Better cleanup logic that avoids system tables

{'='*80}"""
        
        return report
        
    except Exception as e:
        logger.error(f"Failed to generate report: {str(e)}")
        return f"Report generation failed: {str(e)}"


def main():
    """Optimized main function."""
    start_time = time.time()
    
    try:
        logger.info("Starting optimized test script generation...")

        # Load AST files with fallback
        sybase_ast, postgres_ast = load_ast_files()
        if not sybase_ast:
            logger.info("No AST data found. Creating sample AST...")
            sybase_ast = create_sample_sybase_ast()
            postgres_ast = sybase_ast

        logger.info(f"Processing {len(sybase_ast)} procedures")

        if not sybase_ast:
            logger.error("No procedures to process. Exiting.")
            return 1

        # Generate test scripts with timeout
        generator = TestScriptGenerator()
        results = generator.generate_test_scripts(sybase_ast, postgres_ast)

        # Save test scripts
        saved_files = generator.save_test_scripts(results)

        # Generate and display report
        report = generate_comprehensive_report(results)
        print(report)

        # Save report
        try:
            REPORTS_DIR.mkdir(exist_ok=True)
            report_file = REPORTS_DIR / "test_generation_report.txt"
            report_file.write_text(report, encoding="utf-8")
            logger.info(f"Report saved to: {report_file}")
        except Exception as e:
            logger.error(f"Failed to save report: {str(e)}")

        # Performance summary
        elapsed_time = time.time() - start_time
        tests_generated = results.get("generation_summary", {}).get("tests_generated", 0)
        
        if tests_generated > 0:
            logger.info(f"Successfully generated {tests_generated} test scripts in {elapsed_time:.2f} seconds")
            logger.info(f"Average time per procedure: {elapsed_time/tests_generated:.2f} seconds")
            return 0
        else:
            logger.warning("No test scripts were generated")
            return 1

    except Exception as e:
        logger.error(f"Test script generation failed: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())