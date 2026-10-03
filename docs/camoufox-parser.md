# Camoufox public-page parser

Install optional runtime:

```bash
pip install -e ".[camoufox]"
```

Primary uses:
- JS-heavy competitor landing pages;
- pricing/CTA/form extraction;
- public product pages;
- small same-origin crawls for commercial surface inspection.

Default safety contract:
- public HTTP/HTTPS only;
- rejects credential-bearing URLs and local/private addresses;
- optional domain allowlist;
- maximum 25 pages and depth 3;
- challenge/CAPTCHA is detected and reported, not solved;
- no login automation;
- no proxy rotation;
- no authenticated cookie/session import.

The deployment environment should also enforce outbound-network restrictions because
application-level hostname checks are not a substitute for infrastructure egress
controls.


## Network isolation

The browser now routes every HTTP request through the public-URL/domain guard, not
only the initial navigation. By default only the initial hostname is permitted.
Extra CDN/API hostnames must be explicitly added to `allowed_domains`.

This reduces redirect/subresource SSRF risk. Production deployments should still
enforce an outbound-network policy at container/VM level.
