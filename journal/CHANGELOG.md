# Changelog

All notable changes to the AI Trading Journal project will be documented in this file.

---

## Version 1.0 (CLI)

### Sprint 1 — Basic Trade Journal

- Created the main menu system
- Added ability to record trades
- Added ability to view all trades

## Sprint 2 — Trade Management
- Added trade editing
- Added trade deletion
- Improved user input validation

## Sprint 3 — Trade Calculations
- Added automatic Points P/L calculation
- Added Win / Loss / Break-even classification
- Improved trade summaries

## Sprint 4 — Trading Statistics
Added overall trading statistics including:
- Total trades
- Wins
- Losses
- Break-even trades
- Win rate
- Best trade
- Worst trade
- Total Points P/L
- Average Points P/L

## Sprint 5 — Code Refactoring
- Refactored the program into reusable functions
- Improved readability
- Reduced duplicated code

## Sprint 6 — Data Persistence
- Added JSON save/load functionality
- Trades are now stored permanently between sessions

## Sprint 7 — Program Improvements
- Improved input validation
- Improved error handling
- General code cleanup

## Sprint 8 — Auto Save
- Added automatic saving after:
  - Adding trades
  - Editing trades
  - Deleting trades

## Sprint 9 — Trade Dictionaries
- Converted trade records to dictionaries
- Improved code flexibility
- Simplified future feature development

## Sprint 10 — Trade Notes
Added support for:
- Setup
- Session
- Notes
- Mistake tracking

## Sprint 11 — Search & Filtering
Added trade filtering by:
- Symbol
- Direction
- Result
- Setup
- Session

## Sprint 12 — Filtered Statistics
- Added statistics based only on filtered trades
- Reused existing statistics calculations

## Sprint 13 — Trade Date & Time
Added:
- Trade Date
- Entry Time
- Exit Time
- Automatic duration calculation

## Sprint 14 — Contracts & Dollar P/L
Added:
- Number of contracts
- Point value
- Gross Dollar P/L
- Dollar-based statistics

## Sprint 15 — Account Tracking
Added:
- Account Name
- Account Type
- Starting Balance
- Current Balance
- Growth %
- High Water Mark
- Drawdown
- Drawdown %

## Sprint 16 — CSV Export
- Export trades to CSV
- Excel-compatible formatting
- Automatic timestamped export files

## Sprint 17 — Risk Management
Added:
- Risk Amount
- Realized R
- Risk statistics
- Best/Worst R trades

## Sprint 18 — Date Range Filtering
Added:
- Start Date filter
- End Date filter
- Date validation
- Date filtering for:
  - Search
  - Filtered Statistics

## Sprint 19 — Net Performance & Journal Polish

### Commission Tracking
Added:
- Commission
- Net Dollar P/L
- Net Result
- Net Profit statistics

### Performance Analytics
Added:
- Gross Performance
- Net Performance
- Net Profit Factor
- Net Expectancy
- Net Wins/Losses
- Net Win Rate

### Risk Improvements
- Realized R now uses Net Dollar P/L
- Improved risk reporting

### Trade Duration
Added:
- Average Trade Duration
- Longest Trade
- Shortest Trade
- Earliest Entry Time
- Latest Entry Time

### User Interface Improvements
- Redesigned Trading Statistics
- Redesigned Filtered Statistics
- Improved menu layout
- Organized statistics into:
  - Performance Statistics
  - Commission & Net Performance
  - Risk Analytics
  - Trade Duration
- Improved formatting throughout the application
- Standardized output layout

## Sprint 29 — Version 1.1.1 Final Polish and Finalization

Note: Sprints 20-28 (multi-market Futures/Forex support, the multi-file
`journal/` package refactor, and the automated pytest suite) are not yet
documented in this changelog. This entry covers Sprint 29 only.

### Expanded Futures Instrument Support
Added built-in profiles for 9 additional common contracts: ES, NQ, YM,
MYM, RTY, M2K, CL, GC, SI (alongside the existing MES, MNQ, MGC, SIL,
MCL), all sourced from the same centralized profile table. Unrecognized
symbols continue to prompt for a custom tick size and tick value, now
with an explicit "Using a custom Futures profile" confirmation.

### Trading-Time Plausibility Warnings
Adding or editing a Futures or Forex trade now shows a soft warning (with
a "Save this trade anyway? (y/n)" override) when the entered date/time
falls outside approximate Eastern Time market hours -- weekends, the
pre-open portion of Sunday, Friday's close, and (for Futures) the daily
maintenance window. Declining leaves the trade list and data files
completely unchanged. This is an approximation only; it does not model
holidays or early closes.

### Drawdown Terminology Clarity
Account Status now labels its point-in-time figures "Current Drawdown"
and "Current Drawdown Percentage" (previously just "Drawdown" /
"Drawdown Percentage"), matching the terminology already used in Equity
& Drawdown History, so they can no longer be confused with "Maximum
Drawdown."

---

# Current Features

✔ Account Management

✔ Trade Management
- Add Trades
- View Trades
- Edit Trades
- Delete Trades

✔ Trade Information
- Entry
- Exit
- Direction
- Symbol
- Contracts
- Point Value
- Points P/L
- Gross Dollar P/L
- Net Dollar P/L
- Risk
- Realized R
- Commission
- Date
- Time
- Duration
- Setup
- Session
- Notes
- Mistakes

✔ Search & Filtering

✔ Trading Statistics

✔ Filtered Statistics

✔ Account Statistics

✔ CSV Export

✔ Automatic Saving

✔ JSON Database

---

Status:
Current Version: **1.1.1 (CLI)**
Development Status: **Active**