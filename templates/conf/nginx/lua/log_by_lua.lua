local host = ngx.var.host:gsub("^www.", "");
local remote_addr = ngx.var.remote_addr;
metric_requests:inc(1, {host, remote_addr, ngx.var.status});
metric_latency:observe(ngx.now() - ngx.req.start_time(), {host});
metric_request_bytes:observe(tonumber(ngx.var.request_length), {host});
metric_response_bytes:observe(tonumber(ngx.var.bytes_sent), {host});
