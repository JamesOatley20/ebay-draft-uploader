"""HTTP configuration without environment-driven logging or credential files."""

import logging
import ssl

import certifi
import httpx


def silence_network_logging() -> None:
    for name in {"httpx", "httpcore", *logging.root.manager.loggerDict}:
        if name in {"httpx", "httpcore"} or name.startswith(("httpx.", "httpcore.")):
            logger = logging.getLogger(name)
            logger.handlers.clear()
            logger.addHandler(logging.NullHandler())
            logger.propagate = False
            logger.disabled = True


def tls_context() -> ssl.SSLContext:
    # create_default_context() can open SSLKEYLOGFILE before we can disable it.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(cafile=certifi.where())
    context.keylog_filename = None
    return context


def make_client() -> httpx.Client:
    silence_network_logging()
    return httpx.Client(verify=tls_context(), timeout=60, follow_redirects=False, trust_env=False)
