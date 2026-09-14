# Security Policy

## Supported version

Security fixes are applied to the latest release on the default branch.

## Report a vulnerability

Use GitHub's [private vulnerability reporting](https://github.com/NatesVibeCode/harness-fleet/security/advisories/new). Do not open a public issue for an undisclosed vulnerability or include credentials, private source text, or provider responses in a report.

Include the affected version, operating system, reproduction steps, expected result, actual result, and impact. Maintainers will acknowledge a complete report within seven days.

## Data boundary

`test`, `run`, and `resume` transmit selected source slices and task instructions to the configured model provider. SQLite files and exported packets may contain source-derived data and should be protected according to that data's requirements.
