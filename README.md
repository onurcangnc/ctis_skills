# CTIS Skills

<a href="https://www.ctis.bilkent.edu.tr/"><img src="docs/assets/bilkent-ctis-logo.png" alt="Bilkent CTIS" width="640"></a>

One CTIS skill with a command per course. Each command loads the module for that course and carries the same semantic behavior in Codex and Claude Code. The distributed skill text is anonymous: person names never enter the skill's instructions.

Hand-run examples expect the working directory to be `examples/`; run `cd examples` once.

**Fourteen courses have a module and the curriculum has more.** If you have taken one of the open courses, [**take one on**](COLLABORATE.md). The open list, what a module needs, and the steps are all there.

## 📦 1. Install

Claude Code:

```text
claude plugin marketplace add onurcangnc/ctis_skills
claude plugin install ctis@ctis-skills
```

Codex:

```text
codex plugin marketplace add onurcangnc/ctis_skills --ref main
codex plugin add ctis@ctis-skills
```

The two clients are reached differently, because Codex loads skills and does not register a plugin's commands as slash commands.

- **Claude Code**: call the course directly, `/ctis:264` for Python algorithms or `/ctis:474` for an audit finding. The client resolves the name to `commands/264.md`, so nothing is matched or guessed. `/ctis` on its own lets the skill choose the module.
- **Codex**: start with `$ctis` and name the course in the request, `$ctis:259` or `$ctis CTIS259 ...`. The skill reads the course code from what you wrote, says which module it chose, and loads it.

Update, uninstall, and local-package steps live in [INSTALL.md](INSTALL.md).

## ⚙️ 2. What the skill does

Every course is a separate command. [skills/ctis/SKILL.md](skills/ctis/SKILL.md) lists them and loads the matching module from `references/courses/`. A module is self-contained: the teaching posture, the shape the course requires, copy-ready skeletons, "this becomes that" rewrite rules, named failure modes, a verification list, and a workflow. Code, rationale, and verification stay in one flow. The skill is not designed to imitate any person and makes no claim of personal writing fingerprint.

**What the modules rest on.** Each one is derived from one student's collected material for a single section in a single term, and each one opens with an `Evidence note` saying so. That is enough to establish what a course conventionally requires, such as the function signature a lab guide dictates or the dialect a query has to be written in. It is not enough to establish grading weights, submission mechanics, or what an exam covers, and a module that is asked for those says to ask the course instead. Sections differ; if you took the same course elsewhere, [COLLABORATE.md](COLLABORATE.md) is where a second source gets added.

- Codex: 19 canonical skill files plus the commands; [.codex-plugin/plugin.json](.codex-plugin/plugin.json) defines the skill root.
- Claude: 18 semantic files; only `agents/openai.yaml` is dropped. [.claude-plugin/plugin.json](.claude-plugin/plugin.json), [.claude-plugin/marketplace.json](.claude-plugin/marketplace.json), and [plugin.json](plugin.json) define the client bindings.
- Both clients use the same `ctis@ctis-skills` selector. Packages are generated deterministically from the same canonical source tree.

Last verified example run: `24 PASS / 0 SKIP / 0 FAIL` on a machine that has every runtime, and `23 PASS / 1 SKIP (PHP runtime unavailable) / 0 FAIL` without PHP. A SKIP is not counted as a pass, so the suite reports the missing runtime by name instead of quietly passing.

| Package | Members | SHA-256 |
|---|---:|---|
| `ctis.skill` | 19 | `3d0696ea213042c79d5e5d8abce056aa9cf2ca5ac529d56c0a9f99625744fac4` |
| `ctis-codex-plugin.zip` | 34 | `42ea9fced0d5aa555917ad756ff23ca8c38b0db13b2df77f7b6d01cf57b7a3d0` |
| `ctis-claude-plugin.zip` | 35 | `4e5fb67a8ba4a20ae512bdb417a090270d79b7e977db22ad6be7cf5161da958d` |

## 🎓 3. Course map

| Course | Routed work | Example artifact |
|---|---|---|
| [CTIS151](skills/ctis/references/courses/ctis151.md) | Structured C, input and bounds validation | [sentinel_stats.c](examples/ctis151/sentinel_stats.c) |
| [CTIS163](skills/ctis/references/courses/ctis163.md) | Discrete mathematics, relations, counterexample | [relation.json](examples/ctis163/relation.json) |
| [CTIS164](skills/ctis/references/courses/ctis164.md) | Event-driven OpenGL/GLUT graphics and timers | [Source.cpp](examples/ctis164/Source.cpp) |
| [CTIS166](skills/ctis/references/courses/ctis166.md) | Unix shell and deterministic pipelines | [pipeline.sh](examples/ctis166/pipeline.sh) |
| [CTIS255](skills/ctis/references/courses/ctis255.md) | Accessible HTML and browser JavaScript | [app.js](examples/ctis255-256/app.js) |
| [CTIS256](skills/ctis/references/courses/ctis256.md) | PHP/PDO, parameterized queries, escaping | [page.php](examples/ctis255-256/page.php) |
| [CTIS259](skills/ctis/references/courses/ctis259.md) | SQL schema, queries, boundary fixtures | [queries.sql](examples/ctis259/queries.sql) |
| [CTIS262](skills/ctis/references/courses/ctis262.md) | Network topology and verification evidence | [topology.json](examples/ctis262/topology.json) |
| [CTIS264](skills/ctis/references/courses/ctis264.md) | Python algorithms and invariant checks | [merge_ranges.py](examples/ctis264/merge_ranges.py) |
| [CTIS359](skills/ctis/references/courses/ctis359.md) | Decision analysis, assumptions, bounds | [analysis.json](examples/ctis359/analysis.json) |
| [CTIS411](skills/ctis/references/courses/ctis411.md) | Requirements and bidirectional traceability | [project.json](examples/ctis411/project.json) |
| [CTIS417](skills/ctis/references/courses/ctis417.md) | Design patterns, participants, principles | [StrategyDuck.java](examples/ctis417/StrategyDuck.java) |
| [CTIS465](skills/ctis/references/courses/ctis465.md) | .NET vertical slice and verification | [Program.cs](examples/ctis465/Program.cs) |
| [CTIS474](skills/ctis/references/courses/ctis474.md) | Security audit, findings, closing evidence | [audit.json](examples/ctis474/audit.json) |

CTIS 152, 165, 221, 222, 261, 365, 456, 487 and 496 are required courses with no module yet. [COLLABORATE.md](COLLABORATE.md) lists what each one needs.

## ✅ 4. Additional verification examples

Nine runs not tied to a person check runtime and integrated behavior.

| Example | Prompt | argv | Expected stdout |
|---|---|---|---|
| `ctis411-traceability` | Check bidirectional requirement, work, verification, risk, and change-control links in a compact project artifact. | `python check_examples.py CTIS411` | `"EXAMPLE_OK CTIS411\n"` |
| `ctis151-compiled` | Compile with warnings-as-errors and execute normal, invalid, boundary, sentinel, and post-sentinel cases. | `python runtime_checks.py c {runtime}` | `"RUNTIME_OK c\n"` |
| `ctis164-compiled` | Compile and execute line-circle intersection with segment clipping and rejected hits. | `python runtime_checks.py g++ {runtime}` | `"RUNTIME_OK g++\n"` |
| `ctis166-executed` | Execute the quoted pipeline and compare its deterministic output exactly. | `bash ctis166/pipeline.sh` | `"apple\nbanana\npear\n"` |
| `ctis255-javascript-syntax` | Parse-check the interaction layer with the available JavaScript runtime. | `node --check ctis255-256/app.js` | `""` |
| `ctis256-php-syntax` | Lint the PDO pagination boundary when PHP is available. | `php -l ctis255-256/page.php` | `"No syntax errors detected in ctis255-256/page.php\n"` |
| `ctis264-executed` | Execute deterministic normal, duplicate, empty, and input-preservation assertions. | `python ctis264/merge_ranges.py` | `"MERGE_OK\n"` |
| `ctis417-strategy` | Check that the Strategy participants are composed, not inherited, and that the behaviour is interchangeable at runtime. | `python check_examples.py CTIS417` | `"EXAMPLE_OK CTIS417\n"` |
| `ctis465-framework-runtime` | Restore from an empty package source list and execute the framework-only .NET validation slice. | `python runtime_checks.py dotnet {runtime}` | `"RUNTIME_OK dotnet\n"` |

The examples are original and synthetic. They are not copies of a course question or a student submission. The full record lives in [examples/index.json](examples/index.json) and the runner in [tools/run_example_suite.py](tools/run_example_suite.py).

## 🧪 5. Verify it yourself

```text
python -B tools/run_acceptance.py
python -B -m unittest discover -s tests
python -B tools/audit_public_tree.py --tracked
```

The acceptance run ends with `ACCEPTANCE_OK` and covers five gates: source, behavior, packages, docs, and install. It rewrites nothing in the checkout it validates. The reproduction guide is in [docs/TESTING.md](docs/TESTING.md).

The same three commands run on every push and pull request through [`.github/workflows/acceptance.yml`](.github/workflows/acceptance.yml), on a runner that also provides PHP and a JDK, so the hosted run covers examples a Windows laptop usually skips.

## ⚠️ Usage boundaries

This is an independent, unofficial educational and software-assistance work. It does not mean that Bilkent University, CTIS, or any named person has approved or endorsed it. It has no access to private emotions, thoughts, communications, or records; output is not evidence for decisions about a person. For the detailed scope, non-harm intention, academic integrity responsibilities, and correction channel, read the [disclosure notice](DISCLOSURE.md), the [contributing guide](CONTRIBUTING.md), and the [third-party notices](NOTICE.md). To report a source fix or scope issue, use the repository issues channel. Your contributions are welcome; start with the contributing guide.
