#!/usr/bin/env python3
"""
Main Pipeline Runner for Stored Procedure Transformation Validation.
Orchestrates the entire validation process from parsing to final reporting.
"""

import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from config import *

# Setup logging
logging.basicConfig(**LOGGING_CONFIG)
logger = logging.getLogger(__name__)


class ValidationPipeline:
    """Main validation pipeline orchestrator."""
    
    def __init__(self, skip_steps: Optional[List[str]] = None):
        self.skip_steps = skip_steps or []
        self.step_results = {}
        self.start_time = None
        self.end_time = None
    
    def run_full_pipeline(self) -> Dict[str, any]:
        """Run the complete validation pipeline."""
        
        self.start_time = time.time()
        
        pipeline_steps = [
            ("parse", "1_parse_postgres_with_antlr.py", "Parse PostgreSQL procedures with ANTLR"),
            ("compare", "2_compare_asts.py", "Compare ASTs and analyze transformations"),
            ("generate_tests", "generate_test_sql.py", "Generate test scripts using LLM"),
            ("execute_tests", "4_execute_tests_and_compare.py", "Execute tests and compare results"),
            ("generate_report", "5_generate_report.py", "Generate final validation report")
        ]
        
        logger.info("Starting stored procedure transformation validation pipeline")
        logger.info("=" * 80)
        
        # Setup project structure
        self._setup_project_structure()
        
        # Execute pipeline steps
        for step_name, script_name, description in pipeline_steps:
            if step_name in self.skip_steps:
                logger.info(f"Skipping step: {description}")
                self.step_results[step_name] = {"skipped": True}
                continue
            
            logger.info(f"Executing step: {description}")
            result = self._execute_step(step_name, script_name, description)
            self.step_results[step_name] = result
            
            if not result["success"]:
                logger.error(f"Pipeline failed at step: {step_name}")
                if not self._should_continue_on_failure(step_name):
                    break
        
        self.end_time = time.time()
        
        # Generate pipeline summary
        summary = self._generate_pipeline_summary()
        
        logger.info("=" * 80)
        logger.info("Pipeline execution completed")
        logger.info(f"Total execution time: {self.end_time - self.start_time:.2f} seconds")
        
        return summary
    
    def _setup_project_structure(self) -> None:
        """Setup the required project directory structure."""
        
        directories = [
            SAMPLES_DIR,
            ASTS_DIR,
            SCRIPTS_DIR,
            REPORTS_DIR,
            LINEAGE_DIR,
            PROJECT_ROOT / "tests",
            PROJECT_ROOT / "tests" / "sybase",
            PROJECT_ROOT / "tests" / "postgres",
            PROJECT_ROOT / "logs",
            REPORTS_DIR / "charts"
        ]
        
        for directory in directories:
            directory.mkdir(exist_ok=True)
            logger.debug(f"Created directory: {directory}")
        
        # Create sample files if they don't exist
        self._create_sample_files_if_missing()
    
    def _create_sample_files_if_missing(self) -> None:
        """Create sample files if they don't exist."""
        
        # Sample Sybase procedure
        sybase_sample = SAMPLES_DIR / "sybase_proc.sql"
        if not sybase_sample.exists():
            sybase_content = '''-- Sample Sybase Stored Procedure
CREATE PROCEDURE main2
    @batch_id INT,
    @result_msg VARCHAR(255) OUTPUT
AS
BEGIN
    DECLARE @job_id INT
    DECLARE @status_flag VARCHAR(50)
    DECLARE @dynamic_sql VARCHAR(1000)
    DECLARE @temp_value VARCHAR(50)
    
    -- Create temporary table
    CREATE TABLE #my_temp_table (
        job_id INT,
        status VARCHAR(50)
    )
    
    -- Declare cursor
    DECLARE job_cursor CURSOR FOR
        SELECT id FROM jobs WHERE batch_id = @batch_id
    
    OPEN job_cursor
    FETCH NEXT FROM job_cursor INTO @job_id
    
    WHILE @@FETCH_STATUS = 0
    BEGIN
        BEGIN TRY
            IF @job_id = 1
            BEGIN
                SET @status_flag = 'First Job'
            END
            ELSE
            BEGIN
                IF @job_id > 10
                BEGIN
                    SET @status_flag = 'Big Job'
                END
                ELSE
                BEGIN
                    SET @temp_value = 'Regular Job'
                END
            END
            
            IF @status_flag = 'Big Job'
            BEGIN
                INSERT INTO big_jobs (job_id) VALUES (@job_id)
            END
            ELSE
            BEGIN
                INSERT INTO regular_jobs (job_id) VALUES (@job_id)
            END
            
            SET @dynamic_sql = 'UPDATE jobs SET processed = 1 WHERE id = ' + CAST(@job_id AS VARCHAR)
            EXEC(@dynamic_sql)
            
        END TRY
        BEGIN CATCH
            RAISERROR('Error processing job %d', 16, 1, @job_id)
        END CATCH
        
        FETCH NEXT FROM job_cursor INTO @job_id
    END
    
    CLOSE job_cursor
    DEALLOCATE job_cursor
    
    SET @result_msg = 'Batch Processing Complete'
    
    COMMIT TRANSACTION
    
    RETURN 0
END'''
            
            with open(sybase_sample, 'w', encoding='utf-8') as f:
                f.write(sybase_content)
            logger.info(f"Created sample Sybase procedure: {sybase_sample}")
        
        # Sample PostgreSQL procedure (from the provided document)
        postgres_sample = SAMPLES_DIR / "postgres_proc.sql"
        if not postgres_sample.exists():
            postgres_content = '''CREATE OR REPLACE FUNCTION main2(
    batch_id INTEGER,
    result_msg TEXT
)
RETURNS VOID AS $$
DECLARE
    job_id INTEGER;
    status_flag TEXT;
    dynamic_sql TEXT;
    temp_value TEXT;
BEGIN
    CREATE TEMP TABLE my_temp_table (
        job_id INTEGER,
        status TEXT
    );

    DECLARE job_cursor CURSOR FOR
        SELECT id FROM jobs WHERE batch_id = batch_id;

    FETCH job_cursor INTO job_id;

    WHILE FOUND LOOP
        BEGIN
            IF job_id = 1 THEN
                status_flag := 'First Job';
            ELSE
                IF job_id > 10 THEN
                    status_flag := 'Big Job';
                ELSE
                    temp_value := 'Regular Job';
                END IF;
            END IF;

            IF status_flag = 'Big Job' THEN
                INSERT INTO big_jobs (job_id) VALUES (job_id);
            ELSE
                INSERT INTO regular_jobs (job_id) VALUES (job_id);
            END IF;

            dynamic_sql := 'UPDATE jobs SET processed = TRUE WHERE id = ' || CAST(job_id AS TEXT);
            EXECUTE IMMEDIATE dynamic_sql;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE NOTICE 'Default exception handler executed.';
        END;

        FETCH job_cursor INTO job_id;
    END LOOP;

    result_msg := 'Batch Processing Complete';

    COMMIT;

    RETURN 0;
END;
$$ LANGUAGE plpgsql;'''
            
            with open(postgres_sample, 'w', encoding='utf-8') as f:
                f.write(postgres_content)
            logger.info(f"Created sample PostgreSQL procedure: {postgres_sample}")
    
    def _execute_step(self, step_name: str, script_name: str, description: str) -> Dict[str, any]:
        """Execute a single pipeline step."""
        
        script_path = SCRIPTS_DIR / script_name
        
        result = {
            "step_name": step_name,
            "script_name": script_name,
            "description": description,
            "success": False,
            "return_code": None,
            "execution_time": 0.0,
            "output": "",
            "error": "",
            "skipped": False
        }
        
        if not script_path.exists():
            result["error"] = f"Script not found: {script_path}"
            logger.error(result["error"])
            return result
        
        try:
            start_time = time.time()
            
            # Execute the script
            process = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=PROJECT_ROOT
            )
            
            end_time = time.time()
            
            result["return_code"] = process.returncode
            result["execution_time"] = end_time - start_time
            result["output"] = process.stdout
            result["error"] = process.stderr
            result["success"] = process.returncode == 0
            
            if result["success"]:
                logger.info(f"Step completed successfully: {step_name} ({result['execution_time']:.2f}s)")
            else:
                logger.error(f"Step failed: {step_name} (return code: {process.returncode})")
                if result["error"]:
                    logger.error(f"Error output: {result['error']}")
        
        except subprocess.TimeoutExpired:
            result["error"] = "Script execution timed out"
            logger.error(f"Step timed out: {step_name}")
        
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Step execution failed: {step_name} - {str(e)}")
        
        return result
    
    def _should_continue_on_failure(self, step_name: str) -> bool:
        """Determine if pipeline should continue after a step failure."""
        
        # Critical steps that should stop the pipeline
        critical_steps = ["parse", "compare"]
        
        if step_name in critical_steps:
            logger.error(f"Critical step failed: {step_name}. Stopping pipeline.")
            return False
        
        # Non-critical steps can be skipped
        logger.warning(f"Non-critical step failed: {step_name}. Continuing pipeline.")
        return True
    
    def _generate_pipeline_summary(self) -> Dict[str, any]:
        """Generate a summary of the pipeline execution."""
        
        summary = {
            "pipeline_status": "completed",
            "execution_time": self.end_time - self.start_time if self.end_time and self.start_time else 0,
            "steps_executed": len([r for r in self.step_results.values() if not r.get("skipped", False)]),
            "steps_successful": len([r for r in self.step_results.values() if r.get("success", False)]),
            "steps_failed": len([r for r in self.step_results.values() if not r.get("success", False) and not r.get("skipped", False)]),
            "steps_skipped": len([r for r in self.step_results.values() if r.get("skipped", False)]),
            "step_details": self.step_results,
            "critical_failures": [],
            "warnings": [],
            "overall_success": True
        }
        
        # Check for critical failures
        for step_name, result in self.step_results.items():
            if not result.get("success", False) and not result.get("skipped", False):
                if step_name in ["parse", "compare"]:
                    summary["critical_failures"].append({
                        "step": step_name,
                        "error": result.get("error", "Unknown error")
                    })
                    summary["overall_success"] = False
                else:
                    summary["warnings"].append({
                        "step": step_name,
                        "error": result.get("error", "Unknown error")
                    })
        
        # Determine pipeline status
        if summary["critical_failures"]:
            summary["pipeline_status"] = "failed"
        elif summary["warnings"]:
            summary["pipeline_status"] = "completed_with_warnings"
        else:
            summary["pipeline_status"] = "successful"
        
        return summary
    
    def print_summary(self, summary: Dict[str, any]) -> None:
        """Print a formatted summary of the pipeline execution."""
        
        print("\n" + "="*80)
        print("VALIDATION PIPELINE SUMMARY")
        print("="*80)
        print(f"Status: {summary['pipeline_status'].upper()}")
        print(f"Execution Time: {summary['execution_time']:.2f} seconds")
        print(f"Steps Executed: {summary['steps_executed']}")
        print(f"Steps Successful: {summary['steps_successful']}")
        print(f"Steps Failed: {summary['steps_failed']}")
        print(f"Steps Skipped: {summary['steps_skipped']}")
        print()
        
        # Print step details
        print("STEP DETAILS:")
        for step_name, result in summary["step_details"].items():
            status = "SUCCESS" if result.get("success") else "FAILED" if not result.get("skipped") else "SKIPPED"
            execution_time = result.get("execution_time", 0)
            print(f"  {step_name}: {status} ({execution_time:.2f}s)")
        print()
        
        # Print critical failures
        if summary["critical_failures"]:
            print("CRITICAL FAILURES:")
            for failure in summary["critical_failures"]:
                print(f"{failure['step']}: {failure['error']}")
            print()
        
        # Print warnings
        if summary["warnings"]:
            print("WARNINGS:")
            for warning in summary["warnings"]:
                print(f"{warning['step']}: {warning['error']}")
            print()
        
        # Print next steps
        print("NEXT STEPS:")
        if summary["pipeline_status"] == "successful":
            print("Pipeline completed successfully!")
            print("Check the final validation report in reports/final_validation_report.md")
            print("Review charts in reports/charts/")
        elif summary["pipeline_status"] == "completed_with_warnings":
            print("Pipeline completed with warnings")
            print("Review warnings and consider addressing them")
            print("Check the final validation report for details")
        else:
            print("Pipeline failed")
            print("Fix critical issues and re-run the pipeline")
            print("Check logs for detailed error information")
        
        print("="*80)


def create_sample_lineage_files():
    """Create sample lineage files for demonstration."""
    
    LINEAGE_DIR.mkdir(exist_ok=True)
    
    # Sample lineage as provided in the document
    sample_lineage = {
        "main2": {
            "type": "procedure",
            "calls": []
        },
        "jobs": {
            "type": "table",
            "calls": ["main2"],
            "usage": {
                "main2": ["read"]
            }
        },
        "big_jobs": {
            "type": "table",
            "calls": ["main2"],
            "usage": {
                "main2": ["write"]
            }
        },
        "regular_jobs": {
            "type": "table",
            "calls": ["main2"],
            "usage": {
                "main2": ["write"]
            }
        },
        "my_temp_table": {
            "type": "table",
            "calls": ["main2"],
            "usage": {
                "main2": ["create", "read_write"]
            }
        }
    }
    
    # Save Sybase lineage
    sybase_lineage_file = LINEAGE_DIR / "sybase_lineage.json"
    if not sybase_lineage_file.exists():
        import json
        with open(sybase_lineage_file, 'w', encoding='utf-8') as f:
            json.dump(sample_lineage, f, indent=2)
        logger.info(f"Created sample Sybase lineage: {sybase_lineage_file}")
    
    # Save PostgreSQL lineage (same for demo)
    postgres_lineage_file = LINEAGE_DIR / "postgres_lineage.json"
    if not postgres_lineage_file.exists():
        import json
        with open(postgres_lineage_file, 'w', encoding='utf-8') as f:
            json.dump(sample_lineage, f, indent=2)
        logger.info(f"Created sample PostgreSQL lineage: {postgres_lineage_file}")


def main():
    """Main function with command line interface."""
    
    parser = argparse.ArgumentParser(
        description="Stored Procedure Transformation Validation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_validation_pipeline.py                    # Run full pipeline
  python run_validation_pipeline.py --skip generate_tests execute_tests  # Skip test generation and execution
  python run_validation_pipeline.py --step parse       # Run only parsing step
  python run_validation_pipeline.py --verbose          # Enable verbose logging
        """
    )
    
    parser.add_argument(
        "--skip",
        nargs="+",
        choices=["parse", "compare", "generate_tests", "execute_tests", "generate_report"],
        help="Skip specific pipeline steps"
    )
    
    parser.add_argument(
        "--step",
        choices=["parse", "compare", "generate_tests", "execute_tests", "generate_report"],
        help="Run only a specific step"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--create-samples",
        action="store_true",
        help="Create sample files and exit"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create sample files if requested
    if args.create_samples:
        print("Creating sample files...")
        pipeline = ValidationPipeline()
        pipeline._setup_project_structure()
        create_sample_lineage_files()
        print("Sample files created successfully!")
        return 0
    
    try:
        # Determine which steps to skip
        skip_steps = args.skip or []
        
        # If specific step is requested, skip all others
        if args.step:
            all_steps = ["parse", "compare", "generate_tests", "execute_tests", "generate_report"]
            skip_steps = [step for step in all_steps if step != args.step]
        
        # Create and run pipeline
        pipeline = ValidationPipeline(skip_steps=skip_steps)
        
        # Create sample lineage files
        create_sample_lineage_files()
        
        # Run pipeline
        summary = pipeline.run_full_pipeline()
        
        # Print summary
        pipeline.print_summary(summary)
        
        # Return appropriate exit code
        if summary["overall_success"]:
            return 0
        else:
            return 1
    
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        return 130
    
    except Exception as e:
        logger.error(f"Pipeline execution failed: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())