# Stored Procedure Transformation Validation Pipeline

An enterprise-level validation system for Sybase to PostgreSQL stored procedure transformations. This pipeline performs comprehensive analysis, testing, and validation to ensure transformation quality and deployment readiness.

## 🏗️ Project Structure

```
project/
├── samples/                          # Sample stored procedures
│   ├── sybase_proc.sql              # Original Sybase procedure
│   └── postgres_proc.sql            # Transformed PostgreSQL procedure
│
├── asts/                            # Generated AST files
│   ├── sybase_ast.json              # Sybase AST (manual/template)
│   └── postgres_ast.json            # PostgreSQL AST (ANTLR-generated)
│
├── lineage/                         # Data lineage information
│   ├── sybase_lineage.json          # Sybase dependency lineage
│   └── postgres_lineage.json        # PostgreSQL dependency lineage
│
├── scripts/                         # Core validation scripts
│   ├── 1_parse_postgres_with_antlr.py    # PostgreSQL AST parser
│   ├── 2_compare_asts.py                 # AST comparison engine
│   ├── 3_generate_test_sql.py            # LLM-powered test generation
│   ├── 4_execute_tests_and_compare.py    # Test execution and comparison
│   └── 5_generate_report.py              # Final report generation
│
├── tests/                           # Generated test scripts
│   ├── sybase/                      # Sybase test scripts
│   └── postgres/                    # PostgreSQL test scripts
│
├── reports/                         # Validation reports
│   ├── charts/                      # Generated visualizations
│   ├── final_validation_report.md   # Comprehensive markdown report
│   ├── ast_comparison_results.json  # Detailed AST comparison
│   └── test_execution_results.json  # Test execution results
│
├── logs/                            # Application logs
├── config.py                        # Configuration settings
├── requirements.txt                 # Python dependencies
├── run_validation_pipeline.py       # Main pipeline orchestrator
└── README.md                        # This file
```

## 🚀 Features

### Core Capabilities
- **ANTLR-based PostgreSQL parsing** with fallback to custom parsers
- **Comprehensive AST comparison** between Sybase and PostgreSQL procedures
- **LLM-powered test generation** with OpenAI integration
- **Automated test execution** and result comparison
- **Data lineage analysis** and dependency mapping
- **Enterprise-grade reporting** with visualizations and recommendations

### Advanced Features
- **Parallel test execution** for improved performance
- **Configurable similarity thresholds** and validation rules
- **Comprehensive error handling** and recovery mechanisms
- **Interactive pipeline orchestration** with step-by-step execution
- **Rich visualization** with charts and metrics
- **Deployment readiness assessment** with actionable recommendations

## 📋 Prerequisites

### System Requirements
- Python 3.8+
- ANTLR4 runtime
- PostgreSQL client libraries
- Sybase/SQL Server connectivity (pymssql)

### Database Access
- **Sybase/SQL Server**: Connection credentials for test execution
- **PostgreSQL**: Connection credentials for test execution
- **Permissions**: CREATE, INSERT, UPDATE, DELETE on test databases

### API Keys
- **OpenAI API Key**: For LLM-powered test generation (optional but recommended)

## 🛠️ Installation

### 1. Clone and Setup
```bash
# Clone the repository
git clone <repository-url>
cd stored-procedure-validation

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
```bash
# Copy and edit configuration
cp config.py.example config.py

# Set database connections
# Set OpenAI API key (if using LLM features)
export OPENAI_API_KEY="your-api-key-here"
```

### 3. Database Setup
```sql
-- Create test databases
-- Sybase/SQL Server
CREATE DATABASE test_validation_sybase;

-- PostgreSQL  
CREATE DATABASE test_validation_postgres;
```

## 🎯 Quick Start

### Run Complete Pipeline
```bash
# Run the full validation pipeline
python run_validation_pipeline.py

# Run with verbose logging
python run_validation_pipeline.py --verbose

# Create sample files for testing
python run_validation_pipeline.py --create-samples
```

### Run Individual Steps
```bash
# Parse PostgreSQL procedures only
python run_validation_pipeline.py --step parse

# Compare ASTs only
python run_validation_pipeline.py --step compare

# Generate tests only
python run_validation_pipeline.py --step generate_tests

# Execute tests only
python run_validation_pipeline.py --step execute_tests

# Generate final report only
python run_validation_pipeline.py --step generate_report
```

### Skip Specific Steps
```bash
# Skip test execution (useful for development)
python run_validation_pipeline.py --skip execute_tests

# Skip test generation and execution
python run_validation_pipeline.py --skip generate_tests execute_tests
```

## 📊 Pipeline Workflow

### Step 1: PostgreSQL AST Parsing
- Parses PostgreSQL stored procedures using ANTLR4
- Generates standardized AST following the defined schema
- Extracts procedure metadata, parameters, variables, and statements
- Creates lineage information for dependency analysis

### Step 2: AST Comparison
- Compares Sybase and PostgreSQL ASTs structurally
- Analyzes transformation quality and identifies differences
- Calculates similarity scores for procedures and components
- Reports critical differences, warnings, and transformation patterns

### Step 3: Test Generation
- Uses LLM (OpenAI GPT-4) to generate comprehensive test cases
- Creates both Sybase and PostgreSQL compatible test scripts
- Includes positive, negative, and edge case scenarios
- Generates setup data and verification queries

### Step 4: Test Execution
- Executes test scripts on both database platforms
- Compares execution results and data consistency
- Measures performance metrics and identifies issues
- Supports parallel execution for improved performance

### Step 5: Report Generation
- Consolidates all validation results
- Generates comprehensive markdown report with visualizations
- Provides actionable recommendations
- Assesses deployment readiness

## 🔧 Configuration

### Database Configuration
```python
DATABASE_CONFIGS = {
    "sybase": {
        "server": "localhost",
        "port": 5000,
        "database": "test_db",
        "username": "sa",
        "password": "password"
    },
    "postgres": {
        "host": "localhost", 
        "port": 5432,
        "database": "test_db",
        "username": "postgres",
        "password": "password"
    }
}
```

### Validation Thresholds
```python
COMPARISON_THRESHOLDS = {
    "similarity_threshold": 0.85,      # Overall acceptance threshold
    "critical_diff_threshold": 0.7,    # Critical issue threshold
    "warning_diff_threshold": 0.5      # Warning threshold
}
```

### LLM Configuration
```python
LLM_CONFIG = {
    "model": "gpt-4",
    "temperature": 0.1,
    "max_tokens": 4000
}
```

## 📈 AST Schema

The pipeline uses a standardized AST schema that supports:

### Procedure Structure
- **Procedure name** and metadata
- **Parameters** with types and modes (IN/OUT/INOUT)
- **Variables** with type definitions
- **Return type** specification

### Statement Types
- Control flow: `IF`, `WHILE`, `FOR_CURSOR_LOOP`
- Data operations: `INSERT`, `UPDATE`, `DELETE`, `SELECT_INTO`
- Cursor operations: `DECLARE_CURSOR`, `OPEN_CURSOR`, `FETCH_CURSOR`, `CLOSE_CURSOR`
- Exception handling: `TRY`, `EXCEPTION_HANDLER`, `RAISE`
- Transactions: `COMMIT`, `ROLLBACK`
- Dynamic SQL: `EXECUTE_DYNAMIC`

### Lineage Information
```json
{
  "procedure_name": {
    "type": "procedure",
    "calls": ["other_procedures"]
  },
  "table_name": {
    "type": "table", 
    "calls": ["procedures_using_table"],
    "usage": {
      "procedure_name": ["read", "write"]
    }
  }
}
```

## 📋 Sample Usage

### Basic Procedure Validation
```python
# Place your procedures in samples/
# - samples/sybase_proc.sql
# - samples/postgres_proc.sql

# Run validation
python run_validation_pipeline.py

# Check results
cat reports/final_validation_report.md
```

### Custom Test Generation
```python
from scripts.generate_test_sql import TestScriptGenerator

generator = TestScriptGenerator()
test_results = generator.generate_test_scripts(sybase_ast, postgres_ast)
```

### AST Comparison
```python
from scripts.compare_asts import ASTComparisonEngine

comparator = ASTComparisonEngine()  
results = comparator.compare_procedures(sybase_ast, postgres_ast)
```

## 📊 Report Features

### Executive Summary
- Overall transformation quality score
- Test coverage metrics
- Critical issues and warnings count
- Deployment readiness assessment

### Detailed Analysis
- Procedure-by-procedure comparison
- Performance metrics and benchmarks
- Data consistency validation results
- Lineage analysis and dependency mapping

### Visualizations
- Quality overview charts
- Test execution results
- Performance comparison graphs
- Issue distribution analysis
- Lineage coverage maps

### Recommendations
- Prioritized action items
- Risk assessment
- Deployment guidance
- Performance optimization suggestions

## 🚨 Troubleshooting

### Common Issues

#### Database Connection Errors
```bash
# Check database connectivity
python -c "import pymssql; print('Sybase OK')"
python -c "import psycopg2; print('PostgreSQL OK')"

# Verify connection strings in config.py
```

#### ANTLR Parsing Errors  
```bash
# Check ANTLR installation
python -c "import antlr4; print('ANTLR OK')"

# Verify SQL syntax in samples/
```

#### LLM API Issues
```bash
# Check OpenAI API key
python -c "import openai; print('OpenAI configured')"

# Verify API key in environment
echo $OPENAI_API_KEY
```

#### Memory/Performance Issues
```bash
# Reduce parallel workers in config.py
TEST_EXECUTION = {
    "parallel_execution": False,
    "max_workers": 2
}
```

### Debug Mode
```bash
# Enable debug logging
python run_validation_pipeline.py --verbose

# Check logs
tail -f logs/validation.log
```

## 🔄 Integration

### CI/CD Integration
```yaml
# GitHub Actions example
name: Procedure Validation
on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run validation pipeline
        run: python run_validation_pipeline.py --skip execute_tests
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

### Custom Extensions
```python
# Custom AST parser
class CustomSybaseParser(ASTGenerator):
    def parse_procedure(self, sql_content):
        # Custom parsing logic
        return ast

# Custom test generator  
class CustomTestGenerator(TestScriptGenerator):
    def generate_custom_tests(self, procedure):
        # Custom test generation
        return tests
```

## 📚 API Reference

### Main Pipeline
```python
pipeline = ValidationPipeline(skip_steps=['execute_tests'])
results = pipeline.run_full_pipeline()
```

### AST Parsing
```python
parser = PostgreSQLASTGenerator()
ast = parser.parse_postgresql_procedure(sql_content)
```

### Test Generation
```python
generator = TestScriptGenerator()
tests = generator.generate_test_scripts(sybase_ast, postgres_ast)
```

### Execution Engine
```python
executor = TestExecutor()
results = executor.execute_all_tests()
```

## 🤝 Contributing

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Code formatting
black . && isort .

# Type checking
mypy scripts/
```

### Adding New Features
1. Create feature branch
2. Add tests for new functionality
3. Update documentation
4. Submit pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### Documentation
- [AST Schema Reference](docs/ast-schema.md)
- [Configuration Guide](docs/configuration.md)
- [Troubleshooting Guide](docs/troubleshooting.md)

### Contact
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Email**: support@example.com

---

**Enterprise-Ready Stored Procedure Validation Pipeline** - Ensuring quality transformations from Sybase to PostgreSQL with comprehensive testing, analysis, and reporting capabilities.