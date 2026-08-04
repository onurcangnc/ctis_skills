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
| `ctis.skill` | 19 | `3d0696ea213042c79d5e5d8abce056aa9cf2ca5ac529d56c0a9f99625744fac4` |
| `ctis-codex-plugin.zip` | 34 | `42ea9fced0d5aa555917ad756ff23ca8c38b0db13b2df77f7b6d01cf57b7a3d0` |
| `ctis-claude-plugin.zip` | 35 | `4e5fb67a8ba4a20ae512bdb417a090270d79b7e977db22ad6be7cf5161da958d` |

For narrower diagnosis, run:

```text
python -B -m unittest tests.test_clean_install -v
python -B -m unittest discover -s tests -v
python -B tools/audit_public_tree.py --tracked
git diff --check
```

The first command covers archive mutations, bounded validators, transactional reporting, and clean-install behavior. The normal full suite has no unit-test skips. The audit checks the exact tracked public tree; it does not approve ignored development files for publication.

## Verified release

Version `1.2.5`, verified on 2026-08-04.

- Full suite: 124 tests, 0 failures, 0 errors, 0 skips.
- `python -B tools/run_acceptance.py`: `ACCEPTANCE_OK`, all five gates pass.
- Examples: 23 PASS, 1 SKIP (`ctis256-php-syntax`, runtime unavailable: php), 0 FAIL on this Windows machine. The hosted run has PHP and reports 24 PASS, 0 SKIP, 0 FAIL.
- GitHub Actions: the tracked-tree audit, the acceptance gates and the full suite pass on `ubuntu-latest`, and the run leaves the checkout unchanged.
- Live slash-command sweep: every command invoked through a real `claude -p "/ctis:<course> …"` call against the installed skill, with the request written in Turkish, and each reply scored on five criteria: explanation in the reader's language, deliverable in English, the shape the module requires, no file written and nothing executed, and a closing `Verified` section when an artifact was produced.
- Sweep on 1.2.0, 14 runs: 68 of 70 checks passed. Both failures were `/ctis:264`, one Turkish comment pair inside the delivered Python and a reply that ended on the last line of code.
- Sweep on 1.2.1, 16 runs with `/ctis:264` repeated three times: 75 of 80 passed. `/ctis:264` closed with `Verified` on two runs of three and `/ctis:166` on none, so the version that was meant to fix the closing rule did not measurably move it. `/ctis:259` regressed and named a schema `ogrenci`/`ders` under a Turkish request, which the 1.2.0 run had written in English.
- These criteria are model-visible behavior, not file contents, so a single clean run is not evidence. Repeating one command three times is what showed the closing rule was holding two times in three rather than always. Runs against different models are not comparable to each other.
- 1.2.2 answers the two reproducible failures: `Close with the Verified section` became a numbered item in each command's contract instead of a trailing sentence, the language rule carries a schema rewrite, and CTIS259 no longer asks for a "readable alias" without saying which language readable means.
- Sweep on 1.2.2, 20 runs on one model with `/ctis:264`, `/ctis:166` and `/ctis:259` repeated three times each: 99 of 100 passed. `/ctis:166` went from none to three of three and `/ctis:259` wrote an English schema on all three, so both fixes held. `/ctis:264` stayed at two of three, unchanged by the fix that repaired the other two.
- That difference is in the prompts, not the courses. `/ctis:264` was the only request in the sweep phrased as build **and** explain, and all three of its failing replies ended on the explanation. A mixed request matched both branches of the command contract, and the branch that reached the end won. 1.2.3 states that a request to build and explain is a build request, and that the explanation precedes the closing section rather than replacing it.
- A sweep that varies one command's phrasing and no other's cannot separate a course problem from a prompt problem. A later sweep should phrase several courses as build-and-explain.
- Sweep on 1.2.3, 22 runs on one model, four courses phrased as build-and-explain three times each against ten phrased plainly: 109 of 110 passed. The closing section held on all twenty runs that produced an artifact, in both groups.
- That result does not settle what caused the earlier failures. It ran against the version that had already patched the mixed-request case, so it measures the patched behavior, not the phrasing. Deciding between the patch working and the earlier failures being variance would need the same mixed prompts run against 1.2.2, and that question is not worth another sweep.
- The one failure was `/ctis:262` answering in English. Its reply opens by reporting that the course file was permission-blocked. `/ctis:163` failed the same criterion in the 1.2.1 sweep and opened by reporting the module file was outside the allowed directories. Both language failures observed across four sweeps arrived with a module read failure, and the reply that explains a read failure explains it in English, which then sets the language for everything after it.
- 1.2.4 states what to do when the module cannot be read: report it in one line in the language of the request, and continue on the command file's own rules, which do not depend on the module. Two co-occurrences are a thin basis for a fix; this one is cheap and cannot regress a run where the module loads.
- Both clients report the current version after an update, and the installed trees carry 14 commands and 14 course modules.
- The installed `route_ctis.py` is gone; each course is served by its own command contract, and the per-course `commands/*.md` files are what resolve `/ctis:<course>`.
- Package hashes reproduced exactly from the tracked `dist/` (see table above).
