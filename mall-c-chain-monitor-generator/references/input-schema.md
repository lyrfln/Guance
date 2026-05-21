# Input Schema

The generator accepts XLSX, CSV, or JSON.

## Customer Table Columns

Ask the customer to provide these columns:

| Required | Column name | Meaning | Example |
|---:|---|---|---|
| Yes | `业务系统名称` | Business system name; also the only monitor tag and overall monitor suffix | `傲雷商城` |
| Yes | `业务链路` | Key business chain name | `登录链路` |
| Yes | `业务域` | Per-chain monitor suffix | `登录业务` |
| Yes | `关键接口` | One or more key API resources | `/auth/user/login;/customer/api/login/get` |
| Yes | `P90阈值(ms)` | P90 latency threshold in ms | `500` |
| Yes | `P99阈值(ms)` | P99 latency threshold in ms | `1000` |
| Optional | `HTTP异常率阈值` | HTTP 4xx/5xx anomaly threshold | `1` |
| Optional | `APM错误率阈值` | APM error-rate threshold | `1` |

Multiple interfaces in `关键接口` may be separated by:

- newlines;
- `;` or `；`;
- `,` or `，`.

## JSON Format

Either a list:

```json
[
  {
    "name": "登录链路",
    "business": "登录业务",
    "routes": ["/auth/user/login", "/customer/api/login/get"],
    "p90_ms": 500,
    "p99_ms": 1000
  }
]
```

Or an object:

```json
{
  "system_name": "傲雷商城",
  "overall": {
    "p90_ms": 1000,
    "p99_ms": 2000,
    "http_threshold": "1",
    "error_threshold": "1"
  },
  "chains": [
    {
      "name": "登录链路",
      "business": "登录业务",
      "routes": ["/auth/user/login", "/customer/api/login/get"],
      "p90_ms": 500,
      "p99_ms": 1000
    }
  ]
}
```

## Route Normalization

By default, the script prepends `/api` when the route does not already start with `/api/`.

Examples:

- `/auth/user/login` -> `/api/auth/user/login`
- `/api/auth/user/login` -> `/api/auth/user/login`

Disable this behavior with `--no-api-prefix` if the customer's `resource` values already match the actual APM resource exactly.

## Dynamic Routes

Dynamic routes are converted to prefix filters.

Examples:

| Input route | Generated filter |
|---|---|
| `/product/api/detail/{productId}` | ``resource = match('/api/product/api/detail/')`` |
| `/order/api/getOrderDetailByOrderNo/{orderNo}` | ``resource = match('/api/order/api/getOrderDetailByOrderNo/')`` |

Supported placeholder styles include `{id}`, `:id`, and `<id>`.

## Threshold Rules

- Per-chain P90/P99 thresholds must be provided by the customer.
- Overall P90/P99 default to the maximum P90/P99 among all chains unless explicitly provided by CLI or JSON `overall`.
- HTTP/APM thresholds default to the reviewed template style threshold `1` unless provided by table, JSON, or CLI.
