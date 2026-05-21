---
name: mall-c-chain-monitor-generator
description: Generate Guance monitor JSON from a customer business-system key-interface SLI table. Use when the user wants one importable monitor JSON that includes both every key business chain and the overall business system, with four monitor types per scope: HTTP status anomaly rate, APM error rate, P99 latency, and P90 latency.
---

# Business System SLI Monitor Generator

Use this skill to generate Guance monitor JSON for a business system's key interfaces. It takes a reviewed 4-monitor template plus a customer-provided key business interface table, then outputs **one monitor JSON** containing:

- 4 monitors for each key business chain.
- 4 monitors for the overall business system.

The fixed monitor order is:

1. HTTP status anomaly rate.
2. APM error rate.
3. P99 latency.
4. P90 latency.

## When To Use

Use this skill when the user wants to batch-generate Guance monitors for SLO/SLI evaluation from a business interface inventory, especially when they need:

- per-chain key business monitors;
- an overall business-system SLI monitor set;
- naming consistent with the reviewed Guance monitor style;
- dynamic path variables handled safely;
- a single importable monitor JSON.

Do not use it for generic component metrics that are better handled by the generic `monitor` skill.

## Required Customer Inputs

Ask the customer to provide a business-system key interface table in XLSX, CSV, or JSON.

Required columns / fields:

| Field | Chinese column examples | Required | Notes |
|---|---|---:|---|
| Business system name | `业务系统名称`, `业务系统`, `系统名称` | Yes | Used as the only monitor tag and as the overall monitor suffix, e.g. `傲雷商城`. Can also be passed by `--system-name`. |
| Business chain | `业务链路`, `关键业务链路`, `链路名称` | Yes | One chain maps to four monitors. |
| Business suffix | `业务域`, `业务名称`, `告警业务名` | Yes | Used in per-chain monitor titles, e.g. `登录业务`. |
| Key interfaces | `关键接口`, `接口列表`, `接口`, `routes` | Yes | Multiple interfaces can be separated by newlines, semicolons, Chinese semicolons, or commas. |
| P90 threshold | `P90阈值(ms)`, `P90阈值`, `p90_ms` | Yes | Milliseconds. |
| P99 threshold | `P99阈值(ms)`, `P99阈值`, `p99_ms` | Yes | Milliseconds. |
| HTTP anomaly threshold | `HTTP异常率阈值`, `HTTP异常状态占比阈值` | Optional | Defaults to the reviewed template style threshold `1`. |
| APM error threshold | `APM错误率阈值`, `Span错误率阈值`, `错误率阈值` | Optional | Defaults to the reviewed template style threshold `1`. |

For JSON input, use either a list of chain objects or an object with `system_name` and `chains`. See [input-schema.md](references/input-schema.md).

## Required Workflow

1. Read this `SKILL.md`.
2. If the customer provides XLSX/CSV, inspect the table header and confirm it maps to the required fields.
3. Use `scripts/generate_monitors.py` to generate **one JSON**. Do not split files unless the user explicitly asks for debugging artifacts.
4. Generate DQL files with `scripts/export_target_dql.py`.
5. Validate exported DQL with `dqlcheck`. If `dqlcheck` is unavailable, mark the output as `UNVERIFIED`.
6. Return the generated JSON path, DQL validation result path, and any assumptions.

## Naming Rules

Keep monitor names aligned with the reviewed single-chain style.

For each chain, use the chain's business suffix:

```text
{{project}}产品服务{{service}} 接口{{resource}}响应状态码{{http_status_code}}异常率告警-<业务域>
{{project}}产品服务{{service}}关键业务接口{{resource}}异常错误率告警-<业务域>
{{project}}产品服务{{service}}关键业务接口{{resource}} P99响应时间连续超过阈值-<业务域>
{{project}}产品服务{{service}}关键业务接口{{resource}} P90响应时间连续超过阈值-<业务域>
```

For the overall business system, replace `<业务域>` with the business system name:

```text
{{project}}产品服务{{service}} 接口{{resource}}响应状态码{{http_status_code}}异常率告警-傲雷商城
{{project}}产品服务{{service}}关键业务接口{{resource}}异常错误率告警-傲雷商城
{{project}}产品服务{{service}}关键业务接口{{resource}} P99响应时间连续超过阈值-傲雷商城
{{project}}产品服务{{service}}关键业务接口{{resource}} P90响应时间连续超过阈值-傲雷商城
```

## Tag Rule

Only add one tag to every generated monitor:

```json
[{"name": "<业务系统名称>"}]
```

Do not add extra tags such as `总体SLO`, `SLI`, or chain names unless the user explicitly asks.

## Route Handling

Use the same route handling for per-chain and overall monitors:

- if a route already starts with `/api/`, keep it;
- otherwise prepend `/api` by default;
- static routes go into ``resource IN [...]``;
- dynamic routes such as `/detail/{productId}` become prefix filters such as ``resource = match('/api/product/api/detail/')``;
- keep `extend.querylist[].query.filters` aligned with target DQL filters.

## Script Usage

Default one-click generation:

```powershell
python mall-c-chain-monitor-generator/scripts/generate_monitors.py `
  --input customer-key-interfaces.xlsx `
  --system-name 傲雷商城 `
  --output output/monitor/aolai-mall-sli.json `
  --filters-report output/monitor/aolai-mall-resource-filters.md `
  --summary output/monitor/aolai-mall-summary.md
```

Optional reviewed template override:

```powershell
python mall-c-chain-monitor-generator/scripts/generate_monitors.py `
  --template reviewed-4-checker-template.json `
  --input customer-key-interfaces.xlsx `
  --output output/monitor/business-sli.json
```

DQL export:

```powershell
python mall-c-chain-monitor-generator/scripts/export_target_dql.py `
  --input output/monitor/business-sli.json `
  --out-dir output/monitor/dql `
  --include-querylist
```

## References

- Input schema and customer table requirements: [input-schema.md](references/input-schema.md)
- Operational best practices: [best-practices.md](references/best-practices.md)
- Example chain inventory: [mall-c-chains.example.json](references/mall-c-chains.example.json)
- Built-in reviewed template: [reviewed-4-checker-template.json](references/reviewed-4-checker-template.json)
- Customer CSV template: [customer-interface-template.csv](references/customer-interface-template.csv)
