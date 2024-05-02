# external-secrets-bw

## Summary

This project is a small wrapper around `bw serve` command to be used as webhook provider
for `external-secrets-operators` (https://external-secrets.io/latest/).

## Prerequisites

This project needs `bw` command (https://bitwarden.com/help/cli/#download-and-install).

## Launch

**Beware that this command exposes your bitwarden passwords on network (like `bw serve` command does).**

```
export BW_USER=xxx
export BW_PASSWORD=xxx
hatch run uvicorn external_secrets_bw.app:app --port 8000
```

## License

`external-secrets-bw` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
