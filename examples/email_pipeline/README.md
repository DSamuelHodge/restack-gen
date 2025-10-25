# Email Pipeline Example

This example demonstrates a complex email processing pipeline using restack-gen's parallel and conditional operators.

## Overview

This pipeline processes emails through multiple stages with parallel and conditional execution:
1. **EmailValidator** - Validates incoming email
2. **SpamChecker** ⇄ **VirusScanner** - Parallel security checks
3. **EmailRouter** - Routes based on validation results
4. **PersonalHandler** / **BusinessHandler** - Conditional handling

## Pipeline Expression

```
EmailValidator → (SpamChecker ⇄ VirusScanner) → EmailRouter →? (PersonalHandler, BusinessHandler)
```

## Project Structure

```
email_pipeline/
├── README.md                    # This file
├── pyproject.toml              # Project configuration
├── settings.yaml               # Restack configuration
├── src/
│   └── email_pipeline/
│       ├── __init__.py
│       ├── service.py          # Main service entry point
│       ├── agents/
│       │   ├── email_validator.py
│       │   ├── spam_checker.py
│       │   ├── virus_scanner.py
│       │   ├── email_router.py
│       │   ├── personal_handler.py
│       │   └── business_handler.py
│       └── workflows/
│           └── email_pipeline_workflow.py
└── tests/
    ├── test_email_validator.py
    ├── test_spam_checker.py
    ├── test_virus_scanner.py
    ├── test_email_router.py
    ├── test_personal_handler.py
    ├── test_business_handler.py
    └── test_email_pipeline_workflow.py
```

## Setup

This example was generated using the following commands:

```bash
# Initialize project
restack init email_pipeline
cd email_pipeline

# Generate agents
restack g agent EmailValidator
restack g agent SpamChecker
restack g agent VirusScanner
restack g agent EmailRouter
restack g agent PersonalHandler
restack g agent BusinessHandler

# Generate pipeline workflow with parallel and conditional operators
restack g pipeline EmailPipeline --operators "EmailValidator → (SpamChecker ⇄ VirusScanner) → EmailRouter →? (PersonalHandler, BusinessHandler)"
```

## Running the Pipeline

1. Install dependencies:
   ```bash
   pip install -e .
   ```

2. Start the Restack service:
   ```bash
   make dev
   ```

3. In another terminal, run the workflow:
   ```bash
   python client/run_workflow.py
   ```

## How It Works

The pipeline demonstrates advanced orchestration patterns:

### Sequential Flow
- **EmailValidator** first validates the email structure and content

### Parallel Execution (⇄)
- **SpamChecker** and **VirusScanner** run concurrently for efficiency
- Both must complete before proceeding to the next stage

### Conditional Routing (→?)
- **EmailRouter** analyzes the email and sets `email_type` in result
- If `email_type == "personal"`, route to **PersonalHandler**
- Otherwise, route to **BusinessHandler**

## Use Cases

This pattern is useful for:
- Email processing systems
- Content moderation pipelines
- Multi-stage validation workflows
- Conditional business logic

## Customization

You can modify the agents to:
- Integrate with real spam detection APIs
- Connect to virus scanning services
- Implement sophisticated routing logic
- Add more conditional branches
- Add notification handlers

The pipeline workflow is automatically generated and can be regenerated with different operator expressions.
