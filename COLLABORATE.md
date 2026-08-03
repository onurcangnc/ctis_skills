# Collaborate

Fourteen courses have a module. The CTIS curriculum has more, and several of the gaps are courses students ask about most. If you have taken one of the open courses, you can close a gap.

## What is covered

| Command | Course | Year |
|---|---|---|
| `/ctis:151` | Introduction to Programming | 1 |
| `/ctis:163` | Discrete Mathematics | 1 |
| `/ctis:164` | Technical Mathematics with Programming | 1 |
| `/ctis:166` | Information Technologies | 1 |
| `/ctis:255` | Frontend Web Technologies | 2 |
| `/ctis:256` | Introduction to Backend Development | 2 |
| `/ctis:259` | Database Management Systems and Applications | 2 |
| `/ctis:264` | Computer Algorithms | 2 |
| `/ctis:359` | Principles of Software Engineering | 3 |
| `/ctis:411` | Senior Project I | 4 |
| `/ctis:262` | Computer Networks II | elective |
| `/ctis:417` | Software Design Patterns | elective |
| `/ctis:465` | Microservice Development | elective |
| `/ctis:474` | Information Systems Auditing | elective |

## What is open

Required courses with no module yet, in the order they appear in the curriculum.

| Course | Name | Year | What a module needs |
|---|---|---|---|
| CTIS 152 | Algorithms and Data Structures | 1 | the language and the data structures the labs assign, the required function signatures, how solutions are graded |
| CTIS 165 | Fundamentals of Information Systems | 1 | the analysis vocabulary, the deliverable format, what a good answer looks like |
| CTIS 221 | Object Oriented Programming | 2 | the language, the class design rules, what the labs check |
| CTIS 222 | Object Oriented Analysis and Design | 2 | the diagram set, the notation, the review criteria |
| CTIS 261 | Fundamentals of Computer Networks | 2 | the topology exercises and the verification commands, the submission rules |
| CTIS 365 | Applied Data Analysis | 3 | the toolset, the report shape, how results must be evidenced |
| CTIS 487 | Mobile Application Development | 3 | the platform and framework, the project rubric |
| CTIS 456 | Senior Project II | 4 | the deliverables that differ from Senior Project I |
| CTIS 496 | Computer and Network Security | 4 | the topic sequence, the exercise format, what an accepted answer proves |

Electives are welcome too. CTIS 417 Software Design Patterns was added this way, from lecture material a student had kept.

Internship courses, CTIS 290 and CTIS 310, are not taught in a classroom and are out of scope.

## How to add a course

A module is not a summary of lecture notes. It is a set of rules a model can execute, derived from what the course actually required.

1. **Gather what you have.** Lab guides, assignment briefs, graded feedback, your own solutions, the project rubric. The more the material states a rule, the stronger the module.
2. **Extract the rules, not the content.** What the course names its functions, which structure a submission must follow, which tool is required and which is banned, where marks are lost. A rule you can check beats a paragraph you can only read.
3. **Write the module** in `skills/ctis/references/courses/ctis<code>.md`. Keep the six fixed sections that every module has: `Teaching posture`, `Scope`, `Rules with rewrites`, `Failure modes`, `Verification`, `Workflow`. Between `Scope` and `Rules with rewrites`, add the section that names the shape this course requires; the existing modules show the range, from `The four-step template` to `The audit chain`.
4. **Write the command** in `commands/<code>.md`, following any existing command file.
5. **Register it** in the command table in `skills/ctis/SKILL.md`.
6. **Run the gates** before opening a pull request:

```text
python -B tools/run_acceptance.py
python -B -m unittest discover -s tests
python -B tools/audit_public_tree.py --tracked
```

The acceptance run must end with `ACCEPTANCE_OK`.

## What does not go in

The rules in [CONTRIBUTING.md](CONTRIBUTING.md) hold for every contribution, and two of them decide most questions:

**No raw course material.** Lab guide PDFs, assignment briefs, exam papers, slide decks, recorded lectures and student submissions stay out of the repository, including your own. Read them, derive the rule, write the rule. The tree audit rejects those file types and it runs as part of the acceptance gate.

**No person in the skill text.** No names, titles, email addresses or room numbers under `skills/` or `commands/`. A module describes what a course requires and how it is taught, never who teaches it. Nothing about anyone's character, mood, or private life belongs anywhere in this repository.

Course facts and images come from official `bilkent.edu.tr` pages, and every image is declared in `docs/assets/sources.json`.

## Where to start

Open an issue naming the course you want to take on, so two people do not write the same module twice. If you are unsure whether your material is enough, describe what you have in the issue and ask.
