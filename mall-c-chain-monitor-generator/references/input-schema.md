# Input Schema

The generator expects a JSON file containing a list of chain objects.

## Required fields

Each chain object must contain:

```json
{
  "name": "商品浏览链路",
  "business": "商品浏览业务",
  "routes": [
    "/product/api/search",
    "/product/api/detailInfo",
    "/product/api/detail/{productId}",
    "/product/api/categoryNodes"
  ],
  "p90_ms": 500,
  "p99_ms": 1000
}
```

## Field meanings

- `name`: Human-readable chain name.
- `business`: Business suffix appended to monitor titles.
- `routes`: Core interface list for this chain.
- `p90_ms`: Threshold for the P90 latency monitor.
- `p99_ms`: Threshold for the P99 latency monitor.

## Route normalization

The script normalizes routes like this:
- `/auth/user/login` becomes `/api/auth/user/login`
- `/api/auth/user/login` stays unchanged

## Dynamic route rule

If a route contains a placeholder such as `{productId}` or `{orderNo}`, the script:
- excludes that templated route from the static `IN` list
- adds a `match('/prefix/')` condition based on the fixed prefix before `{`

Example:

```json
{
  "routes": [
    "/product/api/detail/{productId}"
  ]
}
```

Generates:

```text
`resource` = match('/api/product/api/detail/')
```

## Template expectations

The template JSON must contain exactly 4 monitors and follow this order:

1. HTTP status anomaly rate
2. APM error rate
3. P99 latency
4. P90 latency

The generator preserves the template style, messages, and most rule structure, then replaces:
- titles
- DQL
- route filters
- `signId`
- latency thresholds
