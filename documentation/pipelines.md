# Pipeline Documentation

This document provides comprehensive guidance on using restack-gen's pipeline feature to orchestrate complex workflows using operator expressions.

## Table of Contents

1. [Overview](#overview)
2. [Operator Syntax](#operator-syntax)
3. [Pipeline Generation](#pipeline-generation)
4. [Examples](#examples)
5. [Validation](#validation)
6. [Best Practices](#best-practices)
7. [Advanced Patterns](#advanced-patterns)
8. [Troubleshooting](#troubleshooting)

---

## Overview

Pipelines in restack-gen allow you to orchestrate multiple agents, workflows, and functions into complex execution flows using a simple operator syntax. Instead of manually writing workflow code, you can express your pipeline logic declaratively and let restack-gen generate the implementation.

### Key Benefits

- **Declarative syntax** - Express complex logic in a readable format
- **Automatic code generation** - No manual workflow coding required
- **Type-safe** - Generated code is validated and type-checked
- **Flexible orchestration** - Supports sequential, parallel, and conditional execution
- **Easy to modify** - Regenerate pipelines when requirements change

---

## Operator Syntax

### Sequential Operator (`→`)

The sequential operator (`→`) executes resources in order, passing the output of each step as input to the next.

```
Resource1 → Resource2 → Resource3
```

**Generated Code:**
```python
result = await self.execute_activity(resource1_activity, result)
result = await self.execute_activity(resource2_activity, result)
result = await self.execute_activity(resource3_activity, result)
```

**Use Cases:**
- Data processing pipelines
- Multi-stage transformations
- Sequential validation steps

### Parallel Operator (`⇄`)

The parallel operator (`⇄`) executes resources concurrently using `asyncio.gather()`.

```
Resource1 ⇄ Resource2 ⇄ Resource3
```

**Generated Code:**
```python
result1, result2, result3 = await asyncio.gather(
    self.execute_activity(resource1_activity, result),
    self.execute_activity(resource2_activity, result),
    self.execute_activity(resource3_activity, result),
)
# Results are merged
result = {**result1, **result2, **result3}
```

**Use Cases:**
- Independent API calls
- Parallel data fetching
- Concurrent validation checks
- Performance optimization

### Conditional Operator (`→?`)

The conditional operator (`→?`) branches execution based on a condition resource's output.

```
Condition →? (TrueBranch, FalseBranch)
```

**Generated Code:**
```python
result = await self.execute_activity(condition_activity, result)
if result.get("condition_field"):  # Configurable condition
    result = await self.execute_activity(true_branch_activity, result)
else:
    result = await self.execute_activity(false_branch_activity, result)
```

**Use Cases:**
- Business logic routing
- Error handling paths
- Feature flag branching
- User role-based workflows

### Operator Precedence

When combining operators, precedence rules apply:

1. **Parentheses** - Highest precedence
2. **Parallel** (`⇄`) - Medium precedence
3. **Sequential** (`→`) - Lowest precedence

**Example:**
```
A → B ⇄ C → D
```

This is parsed as:
```
A → (B ⇄ C) → D
```

Use parentheses for clarity:
```
A → (B ⇄ C) → D  # Explicit grouping
(A → B) ⇄ (C → D)  # Different grouping
```

---

## Pipeline Generation

### Basic Usage

Generate a pipeline using the `restack g pipeline` command:

```bash
restack g pipeline PipelineName --operators "Resource1 → Resource2 → Resource3"
```

This creates:
- `src/{project}/workflows/{pipeline_name}_workflow.py` - Workflow implementation
- `tests/test_{pipeline_name}_workflow.py` - Test file
- Updates `service.py` with workflow registration

### Resource Naming

Resources can be referenced by:
- **Class name**: `DataFetcher`, `EmailValidator`
- **PascalCase base**: `Fetcher`, `Validator`
- **snake_case**: `data_fetcher`, `email_validator`

All formats are automatically resolved:
```bash
# These are equivalent if you have a DataFetcher agent
restack g pipeline P1 --operators "DataFetcher → Processor"
restack g pipeline P1 --operators "Fetcher → Processor"
restack g pipeline P1 --operators "data_fetcher → processor"
```

### Force Regeneration

Use `--force` to overwrite existing pipeline:

```bash
restack g pipeline DataPipeline --operators "A → B → C" --force
```

This is useful when:
- Modifying operator expression
- Updating pipeline structure
- Fixing generated code

---

## Examples

### Example 1: Data Processing Pipeline

**Scenario:** Sequential data transformation

```bash
restack g pipeline DataPipeline --operators "DataFetcher → DataProcessor → DataSaver"
```

**Workflow:**
1. `DataFetcher` - Fetch data from source
2. `DataProcessor` - Transform and filter data
3. `DataSaver` - Persist to destination

See `examples/data_pipeline/` for complete implementation.

### Example 2: Email Processing Pipeline

**Scenario:** Parallel security checks with conditional routing

```bash
restack g pipeline EmailPipeline --operators "EmailValidator → (SpamChecker ⇄ VirusScanner) → EmailRouter →? (PersonalHandler, BusinessHandler)"
```

**Workflow:**
1. `EmailValidator` - Validate email structure
2. `SpamChecker` ⇄ `VirusScanner` - Run security checks in parallel
3. `EmailRouter` - Determine email type
4. Route to `PersonalHandler` or `BusinessHandler` based on type

See `examples/email_pipeline/` for complete implementation.

### Example 3: Multi-Stage Processing

**Scenario:** Complex pipeline with multiple parallel sections

```bash
restack g pipeline ComplexPipeline --operators "Init → (Stage1 ⇄ Stage2 ⇄ Stage3) → Merge → (Validate ⇄ Audit) → Finalize"
```

**Workflow:**
1. `Init` - Initialize processing
2. Three parallel stages
3. `Merge` - Combine parallel results
4. Parallel validation and audit
5. `Finalize` - Complete processing

### Example 4: Conditional Branching

**Scenario:** Different processing paths based on validation

```bash
restack g pipeline ValidationPipeline --operators "Validate →? (ProcessValid → SaveSuccess, HandleError → NotifyAdmin)"
```

**Workflow:**
- If validation passes: process and save
- If validation fails: handle error and notify admin

---

## Validation

restack-gen provides pipeline validation utilities in `restack_gen.validator`:

### Import Validation

```python
from restack_gen.parser import parse_expression
from restack_gen.validator import validate_pipeline

# Parse operator expression
ir_tree = parse_expression("Agent1 → Agent2 → Agent3", project_dir)

# Validate pipeline structure
validate_pipeline(ir_tree)
```

### Validation Checks

1. **Cycle Detection** - Ensures no circular dependencies
2. **Unreachable Nodes** - All resources must be reachable
3. **Resource Existence** - All referenced resources must exist in project

### Using the Validator

```python
from restack_gen.validator import PipelineValidator

validator = PipelineValidator(ir_tree)

# Run all validations
validator.validate()

# Get execution order
order = validator.get_execution_order()
print(f"Execution order: {' → '.join(order)}")

# Get dependencies
deps = validator.get_dependencies()
for resource, predecessors in deps.items():
    print(f"{resource} depends on: {predecessors}")

# Get metrics
metrics = validator.get_graph_metrics()
print(f"Total resources: {metrics['total_resources']}")
print(f"Parallel sections: {metrics['parallel_sections']}")
print(f"Conditional branches: {metrics['conditional_branches']}")
```

---

## Best Practices

### 1. Design Pipelines for Data Flow

Each resource should:
- Accept input data as a dictionary
- Return output data as a dictionary
- Include relevant metadata in output
- Pass through important context

**Good Example:**
```python
@activity.defn
async def process_data(input_data: dict) -> dict:
    # Process input
    result = transform(input_data["data"])
    
    # Return with metadata
    return {
        **input_data,  # Pass through context
        "processed_data": result,
        "status": "success",
        "timestamp": datetime.now().isoformat(),
    }
```

### 2. Use Parallel Execution Wisely

Parallelize when:
- Operations are independent
- No shared state required
- Performance improvement needed

Avoid parallelizing when:
- Operations have dependencies
- Resource contention possible
- Ordering matters

### 3. Handle Conditional Logic Clearly

For conditional operators:
- Use clear condition resource names (`Router`, `Validator`, `Checker`)
- Document condition field in resource implementation
- Provide meaningful branch names

**Example:**
```python
@activity.defn
async def email_router(input_data: dict) -> dict:
    email_type = determine_type(input_data)
    return {
        **input_data,
        "email_type": email_type,  # Clear condition field
        "route_decision": email_type,
    }
```

### 4. Keep Pipelines Focused

- One pipeline per logical workflow
- Split complex flows into multiple pipelines
- Use clear, descriptive names
- Document pipeline purpose in workflow docstring

### 5. Test Pipelines Thoroughly

```python
@pytest.mark.asyncio
async def test_pipeline_end_to_end():
    """Test complete pipeline execution."""
    workflow = MyPipelineWorkflow()
    
    input_data = {"test": "data"}
    result = await workflow.execute(input_data)
    
    # Verify final result
    assert result["status"] == "complete"
    assert "final_output" in result
```

### 6. Use Type Hints

```python
from typing import Any

@activity.defn
async def my_activity(input_data: dict[str, Any]) -> dict[str, Any]:
    """Process data with type hints."""
    ...
```

---

## Advanced Patterns

### Pattern 1: Fan-Out/Fan-In

Process multiple items in parallel, then aggregate:

```bash
restack g pipeline FanOutFanIn --operators "Split → (Process1 ⇄ Process2 ⇄ Process3) → Aggregate"
```

### Pattern 2: Retry with Fallback

Attempt primary processing, fall back on failure:

```bash
restack g pipeline RetryPattern --operators "Validate →? (PrimaryProcess → SuccessHandler, RetryProcess → FallbackHandler)"
```

### Pattern 3: Multi-Stage Validation

Multiple validation gates with error handling:

```bash
restack g pipeline ValidationGates --operators "ValidateInput → Process → ValidateOutput →? (Success, ErrorHandler → Retry)"
```

### Pattern 4: Conditional Parallelism

Parallel execution based on conditions:

```bash
restack g pipeline ConditionalParallel --operators "Check →? ((FastPath1 ⇄ FastPath2), SlowPath)"
```

### Pattern 5: Pipeline Composition

Combine smaller pipelines into larger ones by calling workflows as activities.

---

## Troubleshooting

### Common Issues

#### Issue: Resource Not Found

**Error:** `Unknown resource: MyAgent`

**Solution:**
- Verify resource exists: `restack g agent MyAgent`
- Check spelling and case
- Ensure resource registered in service.py

#### Issue: Import Errors in Generated Code

**Error:** `ImportError: cannot import name 'my_activity'`

**Solution:**
- Ensure all resources exist before generating pipeline
- Check that activities are properly defined
- Verify service.py has correct imports

#### Issue: Circular Dependencies

**Error:** `ValidationError: Cycle detected: A → B → A`

**Solution:**
- Review pipeline logic
- Break cycles by restructuring workflow
- Use conditional branching to avoid loops

#### Issue: Parallel Results Not Merging

**Problem:** Parallel results overwrite each other

**Solution:**
- Use unique keys in parallel branch outputs
- Implement custom merge logic if needed
- Consider using lists for parallel results

### Debugging Tips

1. **Check Generated Code**
   - Review `workflows/{pipeline_name}_workflow.py`
   - Verify imports and activity names
   - Check condition logic in conditionals

2. **Run Tests**
   ```bash
   pytest tests/test_{pipeline_name}_workflow.py -v
   ```

3. **Validate Pipeline**
   ```python
   from restack_gen.parser import parse_expression
   from restack_gen.validator import validate_pipeline
   
   ir = parse_expression(expr, project_dir)
   validate_pipeline(ir)
   ```

4. **Check Service Registration**
   - Verify workflow in service.py
   - Confirm all activities registered
   - Test service startup

---

## Additional Resources

- **Examples:** See `examples/` directory for working implementations
- **Tests:** See `tests/test_validator.py` for validation examples
- **Source Code:** See `restack_gen/parser.py` and `restack_gen/codegen.py`
- **CLI Reference:** Run `restack g pipeline --help`

---

## Summary

Pipelines in restack-gen provide a powerful way to orchestrate complex workflows:

- ✅ **Sequential** execution with `→`
- ✅ **Parallel** execution with `⇄`
- ✅ **Conditional** branching with `→?`
- ✅ **Automatic** code generation
- ✅ **Validated** structure
- ✅ **Type-safe** implementation

Start with simple sequential pipelines and gradually incorporate parallel and conditional logic as needed. Use the examples as templates and refer to validation utilities to ensure correctness.
