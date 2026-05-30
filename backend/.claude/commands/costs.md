---
description: View cost dashboard and spending analytics
argument-hint: [--period day|week|month] [--history N]
---

# Cost Dashboard

Display Devflow cost tracking and spending analytics.

**Arguments:** $ARGUMENTS

## Instructions

### Step 1: Read Cost Configuration

Read `tooling/.automation/costs/config.json` to get:
- Budget limits (budget_dev, budget_context, budget_review)
- Subscription info (plan, token limit, billing period days)
- Warning/critical thresholds
- Currency settings

### Step 2: Find and Read Session Files

Find all `tooling/.automation/costs/sessions/*.json` files.

For each session, extract:
- session_id, start_time, end_time
- story_key (if set)
- entries with model, input_tokens, output_tokens, cost_usd
- totals

Identify the most recent session as "current session".

### Step 3: Apply Filters (based on $ARGUMENTS)

- `--period day`: Today's sessions only
- `--period week`: Last 7 days
- `--period month`: Last 30 days (default)
- `--history N`: Last N sessions
- `--story KEY`: Filter by story key

### Step 4: Calculate Metrics

- Current session: tokens and cost from most recent session
- Cumulative: sum of ALL sessions in billing period
- Cost by model (opus, sonnet, haiku)
- Cost by story
- Budget usage %
- Subscription token usage %
- Averages per session
- I/O ratio (input tokens / output tokens)
- Days remaining in billing period
- Projected monthly usage (tokens and cost)

### Step 5: Display Dashboard

```
=================================================================
                    DEVFLOW COST DASHBOARD
=================================================================
Plan: [plan] | Tokens: [used]/[limit] ([%]%) | [days] days left
This Session: $[current] | Cumulative: $[total]
=================================================================

PERIOD: [period]                        SESSIONS: [count]

--- TOKEN USAGE ---------------------------------------------
                   This Session         Cumulative
Input:             [in]                 [total_in]
Output:            [out]                [total_out]
Total:             [total]              [grand_total]

I/O Ratio:         [ratio]:1

--- COST BY MODEL -------------------------------------------
[model]            $[cost]  ([%]%)

--- BUDGET STATUS -------------------------------------------
Spent:     $[spent]  /  $[budget]  ([%]%)
[==============================----------------------] [%]%

--- PROJECTIONS ---------------------------------------------
Monthly tokens:    [projected] / [limit] ([%]%)
Monthly cost:      $[projected]
Avg/session:       $[avg] | [tokens] tokens

--- RECENT SESSIONS -----------------------------------------
[id]  [date]  [tokens]  $[cost]  [story]
(last 5)

--- CURRENCIES ----------------------------------------------
$[USD] | E[EUR] | L[GBP] | R$[BRL]
=================================================================
```

Show [WARNING] if budget > 75%, [CRITICAL] if > 90%.
Use K/M suffixes. No emojis.
