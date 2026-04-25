#!/usr/bin/env python3
import argparse
import copy
import hashlib
import json
import uuid
from pathlib import Path


def make_uuid():
    return str(uuid.uuid4())


def make_sign_id(seed: str) -> str:
    return hashlib.md5(seed.encode("utf-8")).hexdigest()


def with_api_prefix(route: str) -> str:
    return route if route.startswith("/api/") else f"/api{route}"


def split_routes(routes):
    static_routes = []
    dynamic_prefixes = []
    for route in routes:
        full_route = with_api_prefix(route)
        if "{" in full_route and "}" in full_route:
            dynamic_prefixes.append(full_route.split("{", 1)[0])
        else:
            static_routes.append(full_route)
    return static_routes, dynamic_prefixes


def routes_literal(static_routes):
    return "[" + ", ".join(f"'{route}'" for route in static_routes) + "]"


def resource_condition(static_routes, dynamic_prefixes):
    parts = []
    if static_routes:
        parts.append(f"`resource` IN {routes_literal(static_routes)}")
    parts.extend(f"`resource` = match('{prefix}')" for prefix in dynamic_prefixes)
    if not parts:
        raise ValueError("Each chain must provide at least one route.")
    if len(parts) == 1:
        return parts[0]
    return f"( {' or '.join(parts)} )"


def resource_filters(filter_type: str, static_routes, dynamic_prefixes):
    filters = []
    if static_routes:
        filters.append(
            {
                "id": make_uuid(),
                "op": "in",
                "name": "resource",
                "type": filter_type,
                "logic": "and",
                "value": "",
                "values": static_routes,
            }
        )
    for prefix in dynamic_prefixes:
        filters.append(
            {
                "id": make_uuid(),
                "op": "match",
                "name": "resource",
                "type": filter_type,
                "logic": "or",
                "value": prefix,
                "values": [],
            }
        )
    return filters


def http_error_a_query(condition):
    return (
        "T::RE(`.*`):(count_distinct(`trace_id`)) "
        f"{{ `http_status_group` IN ['4xx', '5xx'] and {condition} }} "
        "BY `project`, `env`, `service`, `resource`, `http_status_code`"
    )


def http_error_b_query(condition):
    return (
        "T::RE(`.*`):(count_distinct(`trace_id`)) "
        f"{{ {condition} }} "
        "BY `project`, `env`, `service`, `resource`, `http_status_code`"
    )


def http_error_expr_query(condition):
    return f'eval(a/b, a="{http_error_a_query(condition)}", b="{http_error_b_query(condition)}")'


def error_rate_query(condition):
    return (
        'eval(A.a1/B.b1,'
        'A="T::RE(`.*`):(COUNT_DISTINCT(`trace_id`) as a1) '
        f"{{`status` = 'error', {condition} }}  "
        'BY `project`, `env`, `service`, `resource`",'
        'B="T::RE(`.*`):(COUNT_DISTINCT(`trace_id`) as b1) '
        f"{{ {condition} }}  "
        'BY `project`, `env`, `service`, `resource`"'
        ").fill(0)"
    )


def error_rate_window_query(condition):
    return (
        'eval(A.a1/B.b1,'
        'A="<window>T::RE(`.*`):(COUNT_DISTINCT(`trace_id`) as a1) '
        f"{{`status` = 'error', {condition} }}  "
        'BY `project`, `env`, `service`, `resource`</window>",'
        'B="<window>T::RE(`.*`):(COUNT_DISTINCT(`trace_id`) as b1) '
        f"{{ {condition} }}  "
        'BY `project`, `env`, `service`, `resource`</window>"'
        ").fill(0)"
    )


def latency_query(condition, percentile):
    return (
        f'eval(A/1000, A="T::RE(`.*`):(percentile(`duration`, {percentile})) '
        f"{{ {condition} }} "
        'BY `project`, `env`, `service`, `resource`")'
    )


def latency_child_query(condition, percentile):
    return (
        f"T::RE(`.*`):(percentile(`duration`, {percentile})) "
        f"{{ {condition} }} "
        "BY `project`, `env`, `service`, `resource`"
    )


def classify_template_checkers(checkers):
    buckets = {}
    for checker in checkers:
        title = checker.get("jsonScript", {}).get("title", "")
        checker_type = checker.get("jsonScript", {}).get("type", "")
        if "http_status_code" in title or "状态码" in title:
            buckets["http"] = checker
        elif "P99" in title:
            buckets["p99"] = checker
        elif "P90" in title:
            buckets["p90"] = checker
        elif checker_type == "apmCheck":
            buckets["error"] = checker
    required = {"http", "error", "p99", "p90"}
    missing = required - set(buckets)
    if missing:
        raise ValueError(f"Template is missing checker types: {sorted(missing)}")
    return buckets


def build_chain_checkers(template_by_kind, chain):
    static_routes, dynamic_prefixes = split_routes(chain["routes"])
    condition = resource_condition(static_routes, dynamic_prefixes)
    filters_field = resource_filters("field", static_routes, dynamic_prefixes)
    filters_keyword = resource_filters("keyword", static_routes, dynamic_prefixes)
    filters_empty = resource_filters("", static_routes, dynamic_prefixes)

    http_query_a = http_error_a_query(condition)
    http_query_b = http_error_b_query(condition)
    http_query_expr = http_error_expr_query(condition)
    err_query = error_rate_query(condition)
    err_window_query = error_rate_window_query(condition)
    p99_query = latency_query(condition, 99)
    p99_child = latency_child_query(condition, 99)
    p90_query = latency_query(condition, 90)
    p90_child = latency_child_query(condition, 90)

    http_checker = copy.deepcopy(template_by_kind["http"])
    http_checker["jsonScript"]["title"] = f"{{{{project}}}}产品服务{{{{service}}}} 接口{{{{resource}}}}响应状态码{{{{http_status_code}}}}异常率告警-{chain['business']}"
    http_checker["jsonScript"]["targets"][0]["dql"] = http_query_expr
    http_checker["signId"] = make_sign_id(http_checker["jsonScript"]["title"])
    http_checker["extend"]["querylist"][0]["uuid"] = make_uuid()
    http_checker["extend"]["querylist"][0]["query"]["q"] = http_query_a
    if http_checker["extend"]["querylist"][0]["query"]["filters"]:
        http_checker["extend"]["querylist"][0]["query"]["filters"][0]["id"] = make_uuid()
        http_checker["extend"]["querylist"][0]["query"]["filters"][0]["type"] = ""
        http_checker["extend"]["querylist"][0]["query"]["filters"][1:] = filters_empty
    http_checker["extend"]["querylist"][1]["uuid"] = make_uuid()
    http_checker["extend"]["querylist"][1]["query"]["q"] = http_query_b
    http_checker["extend"]["querylist"][1]["query"]["filters"] = filters_keyword
    http_checker["extend"]["querylist"][2]["uuid"] = make_uuid()
    http_checker["extend"]["querylist"][2]["query"]["q"] = http_query_expr

    error_checker = copy.deepcopy(template_by_kind["error"])
    error_checker["jsonScript"]["title"] = f"{{{{project}}}}产品服务{{{{service}}}}关键业务接口{{{{resource}}}}异常错误率告警-{chain['business']}"
    error_checker["jsonScript"]["targets"][0]["dql"] = err_query
    error_checker["jsonScript"]["windowDql"] = err_window_query
    error_checker["signId"] = make_sign_id(error_checker["jsonScript"]["title"])
    error_checker["extend"]["querylist"][0]["uuid"] = make_uuid()
    error_checker["extend"]["querylist"][0]["query"]["q"] = err_query
    error_checker["extend"]["querylist"][0]["query"]["filters"] = filters_field

    p99_checker = copy.deepcopy(template_by_kind["p99"])
    p99_checker["jsonScript"]["title"] = f"{{{{project}}}}产品服务{{{{service}}}}关键业务接口{{{{resource}}}} P99响应时间连续超过阈值-{chain['business']}"
    p99_checker["jsonScript"]["targets"][0]["dql"] = p99_query
    p99_checker["jsonScript"]["checkerOpt"]["rules"][0]["conditions"][0]["operands"] = [str(chain["p99_ms"])]
    p99_checker["jsonScript"]["checkerOpt"]["rules"][1]["conditions"][0]["operands"] = [str(chain["p99_ms"])]
    p99_checker["extend"]["rules"][0]["conditions"][0]["operands"] = [str(chain["p99_ms"])]
    p99_checker["extend"]["rules"][1]["conditions"][0]["operands"] = [str(chain["p99_ms"])]
    p99_checker["signId"] = make_sign_id(p99_checker["jsonScript"]["title"])
    p99_checker["extend"]["querylist"][0]["uuid"] = make_uuid()
    p99_checker["extend"]["querylist"][0]["query"]["q"] = p99_query
    p99_checker["extend"]["querylist"][0]["query"]["children"][0]["q"] = p99_child
    p99_checker["extend"]["querylist"][0]["query"]["children"][0]["filters"] = filters_keyword

    p90_checker = copy.deepcopy(template_by_kind["p90"])
    p90_checker["jsonScript"]["title"] = f"{{{{project}}}}产品服务{{{{service}}}}关键业务接口{{{{resource}}}} P90响应时间连续超过阈值-{chain['business']}"
    p90_checker["jsonScript"]["targets"][0]["dql"] = p90_query
    p90_checker["jsonScript"]["checkerOpt"]["rules"][0]["conditions"][0]["operands"] = [str(chain["p90_ms"])]
    p90_checker["jsonScript"]["checkerOpt"]["rules"][1]["conditions"][0]["operands"] = [str(chain["p90_ms"])]
    p90_checker["extend"]["rules"][0]["conditions"][0]["operands"] = [str(chain["p90_ms"])]
    p90_checker["extend"]["rules"][1]["conditions"][0]["operands"] = [str(chain["p90_ms"])]
    p90_checker["signId"] = make_sign_id(p90_checker["jsonScript"]["title"])
    p90_checker["extend"]["querylist"][0]["uuid"] = make_uuid()
    p90_checker["extend"]["querylist"][0]["query"]["q"] = p90_query
    p90_checker["extend"]["querylist"][0]["query"]["children"][0]["q"] = p90_child
    p90_checker["extend"]["querylist"][0]["query"]["children"][0]["filters"] = filters_keyword

    return [http_checker, error_checker, p99_checker, p90_checker]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Generate Guance monitor JSON from a reviewed 4-checker template.")
    parser.add_argument("--template", required=True, help="Path to the reviewed 4-checker template JSON.")
    parser.add_argument("--chains", required=True, help="Path to the chain list JSON.")
    parser.add_argument("--output", required=True, help="Path to the combined output JSON.")
    parser.add_argument("--split-dir", help="Optional directory for per-chain JSON files.")
    args = parser.parse_args()

    template_path = Path(args.template)
    chains_path = Path(args.chains)
    output_path = Path(args.output)
    split_dir = Path(args.split_dir) if args.split_dir else None

    template = load_json(template_path)
    chains = load_json(chains_path)

    if not isinstance(template, dict) or "checkers" not in template:
        raise ValueError("Template JSON must be an object with a 'checkers' array.")
    if not isinstance(chains, list):
        raise ValueError("Chains JSON must be a list of chain objects.")

    template_by_kind = classify_template_checkers(template["checkers"])

    combined = {"checkers": []}

    for chain in chains:
        for field in ("name", "business", "routes", "p90_ms", "p99_ms"):
            if field not in chain:
                raise ValueError(f"Chain is missing required field: {field}")
        chain_checkers = build_chain_checkers(template_by_kind, chain)
        combined["checkers"].extend(chain_checkers)

        if split_dir:
            split_path = split_dir / f"{chain['name']}.json"
            write_json(split_path, {"checkers": chain_checkers})

    write_json(output_path, combined)


if __name__ == "__main__":
    main()
