# Contributing

Thank you for helping improve this educational reference snapshot.

## Scope

Contributions should improve documentation, privacy safeguards, offline tests, code clarity, or the generic orchestration design.

Do not contribute:

- production adapters or instructions for reconnecting to the retired platform;
- real names, account mappings, contact details, identity data, credentials, logs, screenshots, internal addresses, or private documents;
- reverse-engineered routes, schemas, authentication flows, or operational details;
- dependencies or examples that turn the snapshot into a deployment package.

## Development checks

Before opening a pull request, run:

```bash
python -m compileall -q src tests
python -m unittest discover -s tests -v
```

Also review the complete diff for personal data, credentials, internal endpoints, and generated artifacts.

## Pull requests

- Keep each pull request focused.
- Explain the design or documentation problem being solved.
- Describe privacy and security impact.
- Add or update offline tests when behavior changes.
- Confirm that no private or production material is included.

Security findings must be reported privately according to [SECURITY.md](SECURITY.md), not through a public issue.
