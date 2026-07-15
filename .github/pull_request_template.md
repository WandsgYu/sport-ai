## Summary

Describe the focused change and why it improves the public reference snapshot.

## Validation

- [ ] `python -m compileall -q src tests`
- [ ] `python -m unittest discover -s tests -v`
- [ ] I reviewed the complete diff for secrets, personal data, internal endpoints, logs, generated files, and private documentation.

## Privacy and scope

- [ ] No production adapter, retired-platform reconstruction detail, real identity data, credential, or internal interface information is included.
- [ ] The project remains non-deployable and reference-only.
