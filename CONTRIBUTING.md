# Contributing guide

Contributions cover course modules, examples, and verification tooling. Every change ships with tests.

## Anonymity boundary

The distributed skill text is anonymous. No person name, title, private contact detail, or internal information goes under `skills/ctis`. Names appear only in the repository documents, to show source and contribution context.

Modules carry no claim about emotions, intentions, or private thoughts. Person associations rely only on observable and official course records and are given with evidence class and confidence. See [the disclosure notice](DISCLOSURE.md).

## Source rule

Course, instructor, and image facts come only from official `https://*.bilkent.edu.tr` pages. When a new image is added, its record is written to `docs/assets/sources.json` and [NOTICE.md](NOTICE.md) is updated. An image without a source does not enter the tree.

Course material, exams, assignments, student work, raw archives, caches, databases, executables, and credentials are not added to the repo. `tools/audit_public_tree.py` rejects them.

## Change flow

1. Open a topic branch.
2. Write the failing test first, see it fail (go red), then add the production code.
3. If the payload changed, rebuild the `dist/` trio with `python -B tools/build_ctis_packages.py` and update the member counts and SHA-256 table in [README.md](README.md).
4. Run the full acceptance gate:

```text
python -B tools/run_acceptance.py
python -B -m unittest discover -s tests -v
python -B tools/audit_public_tree.py --tracked
```

The acceptance run must end with `ACCEPTANCE_OK`. The detailed procedure is in [docs/TESTING.md](docs/TESTING.md). A skipped runtime test is not counted as a pass; a missing runtime is reported as a named SKIP.

5. In the pull request description, write the gate statuses, test totals, and example PASS/SKIP/FAIL counts.

## Out of scope

Imitating a person, inferring a writing fingerprint, student timeline data, ready-made assignment solutions that bypass academic integrity rules, and unofficial sources are not accepted.