# Testing the release

Run the complete local acceptance check from the repository root:

```text
python -B tools/run_acceptance.py
```

A successful run ends with `ACCEPTANCE_OK` and transactionally writes the machine report to `tmp/public-acceptance.json`. The report is ignored by Git. It contains five gates: source, behavior, packages, docs, and install.

Acceptance never writes into the checkout it validates. The unit subtotal and the strict example suite run against a disposable copy, no subprocess is given a working directory inside the checkout, and a validator that times out or overflows its output limit is killed together with its grandchildren. The run fingerprints the public tree before and after every gate; if a single byte moved, the report records `source_checkout_non_mutation: fail` and the whole run fails even when all five gates pass.

The install gate extracts each archive into a fresh temporary directory. It validates those explicit paths and does not install, update, or remove an active Codex skill, Claude plugin, or marketplace. Temporary directories are removed automatically.

Optional installed validators are environment evidence. If one is missing, the report records `validator unavailable` as a named skip; it never turns an unavailable check into a pass. The example gate behaves the same way for PHP: `runtime unavailable: php` is one explicit skip when PHP is absent, while every available example must pass.

## Release candidate hashes

The packages gate rebuilds all three artifacts in a temporary directory and requires byte equality with the tracked `dist/`. The accepted state is:

| Package | Members | SHA-256 |
|---|---:|---|
| `ctis.skill` | 19 | `a847a96d8c0ad4cf30f17a83cdb872387748c99d5de8b8d776757486e421fb2d` |
| `ctis-codex-plugin.zip` | 34 | `696effcefb42432658efbd114a17ac47923781bdff29c296919c317d96da86b6` |
| `ctis-claude-plugin.zip` | 35 | `0364e47609d719603773d3a25528fd26b4bb2a1796b3a4d391a4dfe5f0d60d63` |

For narrower diagnosis, run:

```text
python -B -m unittest tests.test_clean_install -v
python -B -m unittest discover -s tests -v
python -B tools/audit_public_tree.py --tracked
git diff --check
```

The first command covers archive mutations, bounded validators, transactional reporting, and clean-install behavior. The normal full suite has no unit-test skips. The audit checks the exact tracked public tree; it does not approve ignored development files for publication.

## Verified release

Last verified on 2026-08-03 at commit `7b30329` (`docs: name frameworks, algorithms, and process model in modules`).

- Full suite: 122 tests, 0 failures, 0 errors, 0 skips.
- `python -B tools/run_acceptance.py`: `ACCEPTANCE_OK`, all five gates pass.
- Examples: 23 PASS, 1 SKIP (`ctis256-php-syntax`, runtime unavailable: php), 0 FAIL.
- Live slash-command smoke test: all 13 commands (`/ctis:151` … `/ctis:474`) invoked through real `claude -p "/ctis:<course> …"` calls against the installed skill; each loaded its module, produced the required shape, and closed with a `Verified` section. The check that carries the new framework clauses, `/ctis:474`, mapped the finding to `COBIT 2019 DSS05.04` and `ISO/IEC 27001 A.9.2.5`.
- The installed `route_ctis.py` is gone; each course is served by its own command contract, and the per-course `commands/*.md` files are what resolve `/ctis:<course>`.
- Package hashes reproduced exactly from the tracked `dist/` (see table above).
