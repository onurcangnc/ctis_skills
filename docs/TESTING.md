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
| `ctis.skill` | 19 | `b4dfe6d5e24057f3e775d650ac40aa532245bece74435d032be834bdc5c95505` |
| `ctis-codex-plugin.zip` | 34 | `6b132a77ed0ff42d4b175d8a66de824909ea80919d39fbfe1d464220ad665e24` |
| `ctis-claude-plugin.zip` | 35 | `834bbe70f286181911249ca9aa5886a4f8fec8ff36b20ccebdf4e0300f467034` |

For narrower diagnosis, run:

```text
python -B -m unittest tests.test_clean_install -v
python -B -m unittest discover -s tests -v
python -B tools/audit_public_tree.py --tracked
git diff --check
```

The first command covers archive mutations, bounded validators, transactional reporting, and clean-install behavior. The normal full suite has no unit-test skips. The audit checks the exact tracked public tree; it does not approve ignored development files for publication.

## Verified release

Version `1.2.1`, verified on 2026-08-04.

- Full suite: 124 tests, 0 failures, 0 errors, 0 skips.
- `python -B tools/run_acceptance.py`: `ACCEPTANCE_OK`, all five gates pass.
- Examples: 23 PASS, 1 SKIP (`ctis256-php-syntax`, runtime unavailable: php), 0 FAIL on this Windows machine. The hosted run has PHP and reports 24 PASS, 0 SKIP, 0 FAIL.
- GitHub Actions: the tracked-tree audit, the acceptance gates and the full suite pass on `ubuntu-latest`, and the run leaves the checkout unchanged.
- Live slash-command sweep: all 14 commands invoked through real `claude -p "/ctis:<course> …"` calls against the installed skill, with the request written in Turkish, and each reply scored on five criteria: explanation in the reader's language, deliverable in English, the shape the module requires, no file written and nothing executed, and a closing `Verified` section when an artifact was produced. Result under 1.2.0: 68 of 70 checks passed. Both failures were `/ctis:264` — two Turkish comments inside the delivered Python, and a reply that ended on the last line of code with no `Verified` section. The same command had passed both criteria on an earlier run of the identical text, so the rule held probabilistically rather than reliably. 1.2.1 rewrites both rules with explicit rewrites and a stated negative case.
- The sweep is the reason the module text carries a comment-language rewrite. A criterion that only a live run can check is worth the runs it costs.
- Both clients report the current version after an update, and the installed trees carry 14 commands and 14 course modules.
- The installed `route_ctis.py` is gone; each course is served by its own command contract, and the per-course `commands/*.md` files are what resolve `/ctis:<course>`.
- Package hashes reproduced exactly from the tracked `dist/` (see table above).
