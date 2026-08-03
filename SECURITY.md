# Security policy

## Supported version

Only the latest state of the `main` branch is supported. Packages are generated from the three artifacts under `dist/`; the verified SHA-256 values are in [README.md](README.md). Compare the digest of a downloaded package against this table before installing it.

## Reporting a vulnerability

Do not open a vulnerability as a public issue. Open a private report from the **Security** tab of the GitHub repository with **Report a vulnerability**. The report must include:

- the affected file or package path,
- the reproduction steps and observed behavior,
- the expected behavior and an impact assessment.

The first-response target is 7 days and a fix or mitigation plan is targeted within 30 days. Do not share details until the fix is published.

No personal contact details of the author(s) are published in this repository; the reporting channel is GitHub only.

## Scope

In scope: the skill router, course modules, example scripts, packaging and verification tools, and the generated `dist/` artifacts.

Out of scope: Bilkent University and CTIS systems, third-party clients (Claude Code, Codex), and infrastructure not tied to this repository. This project is an independent, unofficial work.

## Helping

If you want to contribute, start with the [contributing guide](CONTRIBUTING.md). Report source, scope, or take-down requests through the issue path in the [disclosure notice](DISCLOSURE.md). The examples and generated code should be reviewed before being run. The repository neither stores nor asks for credentials, network access, or student data.