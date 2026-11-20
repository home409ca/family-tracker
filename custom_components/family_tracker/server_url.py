"""Use the Internet URL administered by Home Assistant."""

from urllib.parse import urlsplit


def public_server_url(config):
    value = config.external_url
    if not isinstance(value, str) or any(ch.isspace() or ch == "\\" for ch in value):
        return None
    try:
        parts = urlsplit(value)
        port = parts.port
        if (parts.scheme == "https" and parts.hostname and parts.path in ("", "/")
                and parts.username is None and parts.password is None and not parts.query
                and not parts.fragment and (port is None or 1 <= port <= 65535)):
            return value.rstrip("/")
    except ValueError:
        pass
    return None
