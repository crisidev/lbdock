function password_encode(password)
    local resty_sha256 = require "resty.sha256"
    local str = require "resty.string"
    local sha256 = resty_sha256:new()
    sha256:update(password)
    local digest = sha256:final()
    return str.to_hex(digest)
end

function check_password(password, encoded_password)
    if password_encode(password) == encoded_password then
      return true
    end
    return false
end

function get_user(username)
    --- Defaults
    local host = ngx.var.host:gsub("^www.", "");

    local access_redis_host = ngx.var.access_redis_host or 'redis.{{ config['domain'] }}'
    local access_redis_port = ngx.var.access_redis_port or 6379
    local access_user_catalogue = ngx.var.access_user_catalogue or 'nginx:' .. host
    local access_admin_catalogue = ngx.var.access_admin_catalogue or 'nginx:admins'

    ---

    local redis = require "resty.redis"
    local red = redis:new()

    red:set_timeout(1000)

    local ok, err = red:connect(access_redis_host, access_redis_port)
        if not ok then
            ngx.log(ngx.ERR, "failed to connect to the redis server: ", err)
            ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
        return nil
    end

    local res, err = red:hget(access_user_catalogue, username)

    if res == ngx.null then
        ngx.log(ngx.ERR, "failed to find user " .. username .. " into " .. access_user_catalogue)
        res, err = red:hget(access_admin_catalogue, username)
        if res == ngx.null then
          ngx.log(ngx.ERR, "failed to find user " .. username .. " into " .. access_admin_catalogue)
          return nil
        else
          ngx.log(ngx.ERR, "user " .. username .. " found into " .. access_admin_catalogue)
        end
    else
        ngx.log(ngx.ERR, "user " .. username .. " found into " .. access_user_catalogue)
    end

    return res
end

function authenticate()
    -- Test Authentication header is set and with a value
    local header = ngx.req.get_headers()['Authorization']
    if header == nil or header:find(" ") == nil then
        return false
    end

    local divider = header:find(' ')
    if header:sub(0, divider-1) ~= 'Basic' then
       return false
    end

    local auth = ngx.decode_base64(header:sub(divider+1))
    if auth == nil or auth:find(':') == nil then
        return false
    end

    divider = auth:find(':')
    local username = auth:sub(0, divider-1)
    local password = auth:sub(divider+1)

    local res = get_user(username)

    if res == nil then
        return false
    end

    if check_password(password, res) then
        ngx.log(ngx.ERR, "password authentication successful for " .. username)
        return true
    end

    ngx.log(ngx.ERR, "password authentication failed for " .. username)
    return false
end

local user = authenticate()

if not user then
   local host = ngx.var.host:gsub("^www.", "");
   ngx.header.content_type = 'text/plain'
   ngx.header.www_authenticate = 'Basic realm=""'
   ngx.status = ngx.HTTP_UNAUTHORIZED
   ngx.exit(ngx.HTTP_UNAUTHORIZED)
end
