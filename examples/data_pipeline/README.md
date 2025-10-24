# Data Pipeline Example

This example demonstrates a complete data processing pipeline using restack-gen's operator syntax.

## Overview

This pipeline processes data through three sequential stages:
1. **DataFetcher** - Fetches data from an external source
2. **DataProcessor** - Processes and transforms the data
3. **DataSaver** - Saves the processed data to a destination

## Pipeline Expression

```
DataFetcher → DataProcessor → DataSaver
```

## Project Structure

```
data_pipeline/
├── README.md                    # This file
├── pyproject.toml              # Project configuration
├── settings.yaml               # Restack configuration
├── src/
│   └── data_pipeline/
│       ├── __init__.py
│       ├── service.py          # Main service entry point
│       ├── agents/
│       │   ├── data_fetcher.py
│       │   ├── data_processor.py
│       │   └── data_saver.py
│       └── workflows/
│           └── data_pipeline_workflow.py
└── tests/
    ├── test_data_fetcher.py
    ├── test_data_processor.py
    ├── test_data_saver.py
    └── test_data_pipeline_workflow.py
```

## Setup

This example was generated using the following commands:

```bash
# Initialize project
restack init data_pipeline
cd data_pipeline

# Generate agents
restack g agent DataFetcher
restack g agent DataProcessor
restack g agent DataSaver

# Generate pipeline workflow
restack g pipeline DataPipeline --operators "DataFetcher → DataProcessor → DataSaver"
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

The pipeline orchestrates three agents in sequence:

1. **DataFetcher** receives input data, simulates fetching from an API
2. **DataProcessor** transforms the fetched data (e.g., filtering, enrichment)
3. **DataSaver** persists the processed data to a storage system

Each agent is implemented as a Restack activity, and the pipeline workflow coordinates their execution using the `→` (sequence) operator.

## Customization

You can modify the agents to:
- Connect to real data sources (databases, APIs, files)
- Implement actual data transformations
- Save to different destinations (S3, databases, message queues)

The pipeline workflow is automatically generated and can be regenerated if you change the operator expression.
