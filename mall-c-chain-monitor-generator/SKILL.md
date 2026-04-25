---
name: mall-c-chain-monitor-generator
description: Use when the user wants to generate Guance monitor JSON for mall C-end business chains from a reviewed 4-checker template plus a chain list. Best for workflows that follow the mall C-end SLO inventory: one chain maps to 4 monitors in this order: HTTP status anomaly rate, APM error rate, P99 latency, and P90 latency.
---

# Mall C Chain Monitor Generator

Generate Guance monitor JSON for mall C-end business chains by cloning a manually reviewed 4-checker template and replacing routes, thresholds, titles, and query filters in a consistent way.

Use this skill when:
- the user has already identified business chains and core APIs from a mall C-end SLO inventory
- the user wants a combined monitor JSON or per-chain monitor JSON
- the user wants to preserve the style of an exported Guance template instead of inventing a new JSON structure

Do not use this skill when:
- the user only wants SLO design advice and not monitor JSON
- there is no reviewed template JSON yet
- the user is working on a non-mall or clearly different monitor pattern

## Required Inputs

You need:
- one reviewed template JSON with exactly 4 monitors in this order:
  1. HTTP status anomaly rate
  2. APM error rate
  3. P99 latency
  4. P90 latency
- one chain list JSON that follows [input-schema.md](references/input-schema.md)

If the user has no chain list yet, start from [mall-c-chains.example.json](references/mall-c-chains.example.json).

## Workflow

1. Inspect the reviewed template JSON.
Confirm the four template monitors are still the canonical style the user wants to clone.

2. Inspect the chain list.
Load the chain names, business names, routes, `p90_ms`, and `p99_ms`.

3. Generate monitor JSON with `scripts/generate_monitors.py`.
Default to a combined JSON unless the user explicitly asks for split files.

4. Validate every generated target DQL.
Use `scripts/export_target_dql.py` to extract DQL files, then validate them with the local `dqlcheck` workflow if available.

5. Return the generated file paths and the main assumptions.
If you had to infer route prefixes or thresholds, say so briefly.

## Generation Rules

Always preserve the user's reviewed template style as much as possible.

For each chain, generate exactly 4 monitors:
- HTTP status anomaly rate
- APM error rate
- P99 latency
- P90 latency

### Route handling

Normalize routes like this:
- if a route already starts with `/api/`, keep it
- otherwise prepend `/api`

For static routes:
- keep them in ``resource IN [...]``

For dynamic routes with placeholders like `{productId}`:
- do not rely only on the templated route string
- remove the dynamic route from the static `IN` list
- add an extra condition:
  `` `resource` = match('/fixed/prefix/') ``

Example:
- input route: `/product/api/detail/{productId}`
- generated condition:
  `` `resource` IN ['/api/product/api/search', '/api/product/api/detailInfo'] or `resource` = match('/api/product/api/detail/') ``

### Querylist filters

Keep `extend.querylist[].query.filters` aligned with the target DQL:
- one `in` filter for static routes
- one `match` filter with `logic: "or"` for each dynamic prefix

Do not leave template filters stale after changing the DQL.

### Thresholds

Use the chain definition values:
- `p99_ms` for the P99 monitor
- `p90_ms` for the P90 monitor

Keep the reviewed template's rule structure, match counts, messages, and alert style unless the user explicitly asks to change them.

## Scripts

- `scripts/generate_monitors.py`
  Generate combined or split monitor JSON from a reviewed template and a chain list.

- `scripts/export_target_dql.py`
  Extract `jsonScript.targets[*].dql` to individual `.dql` files for validation.

## References

- Read [best-practices.md](references/best-practices.md) before generating large batches or when refining a template.
- Read [input-schema.md](references/input-schema.md) when preparing or validating chain input files.
- Use [mall-c-chains.example.json](references/mall-c-chains.example.json) as a starting point for a new mall C-end chain inventory.
