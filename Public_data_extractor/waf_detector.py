WAF_SIGNATURES = [
    "mod_security",
    "not acceptable",
    "access denied",
    "forbidden",
    "cloudflare",
    "akamai",
]


def is_waf_block(text: str) -> bool:
    text = text.lower()
    return any(sig in text for sig in WAF_SIGNATURES)
