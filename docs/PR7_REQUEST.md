# PR 7: Pipeline integration & examples — Request

Date: 2025-10-24

## Summary
Add pipeline integration examples and a validation module to restack-gen. Provide documentation illustrating operator syntax, usage patterns, and troubleshooting.

## Objectives
- Create working example pipelines under `examples/`:
	- Data pipeline (sequential)
	- Email pipeline (parallel + conditional)
- Implement `restack_gen/validator.py` for pipeline validation:
	- Cycle detection
	- Unreachable node detection
	- Execution order and dependency mapping
	- Graph metrics (depth, parallel, conditional counts)
- Author `docs/PIPELINES.md` covering usage, patterns, and troubleshooting.

## Acceptance Criteria
- Examples run end-to-end and include tests.
- Validator catches common structural issues with clear messages.
- Documentation is comprehensive and matches implementation.

## Out of Scope
- Visualization UI for pipelines.
- Runtime orchestration engine changes beyond codegen.

## Notes
- Builds on PR 6 (IR → codegen). Ensures IR alignment for Conditional (condition is a string expression).

