prometheus = require("prometheus").init("prometheus_metrics")
metric_requests = prometheus:counter(
  "nginx_http_requests_total", "Number of HTTP requests", {"host", "client", "status"})
metric_latency = prometheus:histogram(
  "nginx_http_request_duration_seconds", "HTTP request latency", {"host"})
metric_request_bytes = prometheus:histogram(
  "nginx_http_request_size_bytes", "Total size of incoming requests", {"host"},
  {10,100,1000,10000,100000,1000000})
metric_response_bytes = prometheus:histogram(
  "nginx_http_response_size_bytes", "Size of HTTP responses", {"host"},
  {10,100,1000,10000,100000,1000000})
