---
description: Learning-first development instructions for the AI Trading Journal project
applyTo: "**"
---

# AI Trading Journal Development Instructions

## Project Context

This project is an AI Trading Journal being built incrementally as a long-term startup project.

The current version is V1.0: a Python-based personal trading journal. The developer is currently learning Python while building the project and is working through features in structured sprints.

The current V1.0 application includes or is developing features such as:
- adding, viewing, editing, and deleting trades
- JSON save and load functionality
- automatic saving
- trade dictionaries
- trade notes, setups, sessions, and mistakes
- search and multi-filter functionality
- overall and filtered statistics
- trade date, time, and duration tracking
- contracts, point values, dollar P/L, risk, and R:R calculations
- future account tracking and CSV export

The long-term roadmap may later include:
- multi-file architecture
- databases
- backend APIs
- frontend dashboards
- user accounts
- AI-powered trade analysis
- strategy-specific journaling
- screenshot analysis
- support for ICT, order flow, supply and demand, futures, FX, indices, commodities, and other markets

## Current Learning Priority

During V1.0, prioritize the developer's learning over maximum development speed.

The developer is still learning Python and currently understands concepts including:
- variables
- user input
- type conversion
- strings
- arithmetic operators
- comparison and logical operators
- if, elif, and else statements
- while loops
- for loops
- lists and list methods
- range()
- tuples
- functions
- dictionaries
- break, continue, and pass
- scope
- return values
- string formatting
- basic JSON persistence
- basic date and time handling

Do not assume knowledge of advanced Python concepts unless they already appear in the project or the developer explicitly asks to learn them.

## Teaching and Assistance Rules

- Prioritize explanation and understanding over automatically completing work.
- When the developer asks a conceptual question, explain the concept clearly before suggesting code.
- When debugging, identify and explain the root cause before proposing a fix.
- When suggesting a fix, prefer the smallest reasonable change.
- Explain unfamiliar syntax or concepts introduced in suggestions.
- Use examples from the existing AI Trading Journal code when possible.
- Guide new sprint features incrementally rather than implementing the entire sprint automatically.
- Do not complete an entire sprint unless explicitly asked.
- Do not rewrite entire files unless explicitly asked.
- Do not make large architectural changes without explaining the reason first.
- Do not silently introduce advanced abstractions.
- Do not replace working beginner-friendly code merely because a shorter or more advanced version exists.
- Preserve opportunities for the developer to write important logic independently.

## Coding Style

- Prefer simple, readable, beginner-friendly Python.
- Preserve the project's existing coding style where reasonable.
- Use descriptive variable and function names.
- Prefer straightforward loops and conditionals when they are easier to understand.
- Avoid unnecessary classes, decorators, generators, lambdas, metaprogramming, complex comprehensions, and advanced design patterns unless explicitly requested or clearly justified.
- Keep functions focused and understandable.
- Avoid unnecessary dependencies.
- Add comments only when they clarify reasoning or non-obvious behavior.
- Do not overengineer V1.0 features.

## Inline Suggestions

When generating inline code suggestions:
- favor short, context-aware completions
- continue the developer's existing pattern
- avoid unexpectedly generating large feature implementations
- avoid introducing advanced syntax without a clear need
- preserve existing variable names and data structures where reasonable

## Code Review

When reviewing code:
- distinguish between actual bugs, potential edge cases, readability improvements, and optional refactors
- do not present optional style preferences as required fixes
- identify risks to existing save/load behavior
- identify risks to trade statistics and filtered statistics
- identify risks to existing JSON trade data
- check for duplicated calculations where relevant
- explain why a change is recommended

## Data Safety

The project stores trade data and may later store account and financial-performance information.

- Avoid destructive changes to existing trade data.
- Preserve backward compatibility with existing `trades.json` data where practical.
- Warn before recommending schema changes that could break older saved trades.
- Prefer safe handling of missing dictionary keys when older trades may not contain newer fields.
- Do not expose secrets, credentials, API keys, tokens, or private user data.

## V1.0 Boundary

Until explicitly told that V1.0 is complete:
- treat this as a learning-first project
- do not autonomously build major features
- do not take over sprint implementation
- do not perform broad repository-wide rewrites
- do not convert the project to an advanced architecture prematurely
- help the developer understand and build the core application personally

After V1.0, more advanced refactoring, testing, databases, multi-file architecture, APIs, frontend development, and agent-assisted workflows may be appropriate.