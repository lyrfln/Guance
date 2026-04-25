# Best Practices

This skill works best when you treat monitor generation as a two-step process:

1. Manually tune one canonical chain template.
2. Batch-generate the rest from that reviewed template.

## 1. Review one chain first

Do not batch-generate before reviewing one real chain in Guance.

The reviewed template should already encode:
- the preferred monitor order
- message style
- alert levels and match counts
- whether to use `apmCheck` or `simpleCheck`
- the fields and group-by dimensions your team wants to keep

For the mall C-end workflow, the current preferred order is:

1. HTTP status anomaly rate
2. APM error rate
3. P99 latency
4. P90 latency

## 2. Keep one chain equal to four monitors

Use one business chain as the unit of monitor generation.

Each chain should map to:
- one HTTP status anomaly rate monitor
- one APM error rate monitor
- one P99 latency monitor
- one P90 latency monitor

Avoid mixing multiple unrelated chains into a single monitor.

## 3. Prefer exported Guance JSON style over invented structures

When a reviewed Guance export exists, clone that structure instead of designing a new one from scratch.

Preserve:
- `jsonScript.type`
- `groupBy`
- message templates
- rule structure
- `querylist` layout

Only change what is chain-specific:
- business title suffix
- route conditions
- thresholds
- identifiers

## 4. Handle dynamic routes conservatively

For routes with placeholders such as `{productId}`:

- do not depend on the templated route string alone
- keep static routes in `resource IN [...]`
- add one extra fallback:
  `` `resource` = match('/fixed/prefix/') ``

This is preferred over large regex expressions because it stays closer to the UI filter model and is easier to read in exported JSON.

## 5. Keep DQL and UI filters in sync

Whenever you change route conditions in:
- `jsonScript.targets[].dql`

also update:
- `extend.querylist[].query.filters`

If these diverge, the monitor may execute one condition while the UI shows another.

## 6. Normalize route prefixes consistently

If your chain inventory is written without `/api`, normalize it before generation.

Examples:
- `/order/api/create` -> `/api/order/api/create`
- `/marketing/api/signInPromotion/get` -> `/api/marketing/api/signInPromotion/get`

Do not mix prefixed and unprefixed routes in the same chain file.

## 7. Validate every generated target DQL

Always validate generated target DQL before import.

Recommended flow:

1. Run `scripts/export_target_dql.py`
2. Validate each exported `.dql` with your local `dqlcheck`

Do not assume a copied query is valid just because a similar chain passed earlier.

## 8. Keep thresholds in the chain inventory

Store `p90_ms` and `p99_ms` inside the chain list JSON instead of hardcoding them in the generator.

Benefits:
- easier review
- easier diffing
- easier future tuning

## 9. Batch import only after spot-checking two chain types

Before importing a large combined file, manually inspect at least:
- one chain with only static routes
- one chain with dynamic path parameters

This catches most route-matching mistakes early.

## 10. Keep source artifacts

Retain:
- the reviewed template JSON
- the chain list JSON
- the generated combined JSON
- the DQL validation output

These are the minimum artifacts needed to safely iterate later.
