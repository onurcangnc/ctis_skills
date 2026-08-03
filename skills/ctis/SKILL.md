---
name: ctis
description: Use when a request involves CTIS course codes or CTIS-style work in C, discrete mathematics, OpenGL/GLUT graphics, Unix text processing, frontend jQuery, PHP/PDO, Oracle SQL, networking, Python algorithms, software engineering estimation and coverage, project documentation, .NET microservices, or IS auditing.
---

# CTIS course modules

Each course is a separate command. Invoke the one that matches the work and stay in that context.

| Command | Course | Work it covers |
|---|---|---|
| `/ctis:151` | CTIS151 | structured C in Visual Studio, validation, menus, functions, arrays, text files |
| `/ctis:163` | CTIS163 | discrete mathematics, quantifiers, proofs, functions, relations, matrices |
| `/ctis:164` | CTIS164 | event-driven OpenGL/GLUT graphics in C++, handlers, timers, state machines |
| `/ctis:166` | CTIS166 | Unix text processing pipelines |
| `/ctis:255` | CTIS255 | frontend web with HTML, CSS, jQuery, localStorage |
| `/ctis:256` | CTIS256 | PHP with PDO, prepared statements, paging, sessions |
| `/ctis:259` | CTIS259 | Oracle SQL on the HR schema |
| `/ctis:262` | CTIS262 | applied networks, VLANs, EtherChannel, DHCP, routing, verification |
| `/ctis:264` | CTIS264 | Python algorithms, recursion, graphs, heaps, pandas, timing |
| `/ctis:359` | CTIS359 | function points, COCOMO, quality models, coverage and MC/DC |
| `/ctis:411` | CTIS411 | project documentation, requirements, WBS, traceability, risk |
| `/ctis:465` | CTIS465 | .NET microservices with MediatR and EF Core |
| `/ctis:474` | CTIS474 | information systems auditing |

Each command loads its module from `references/courses/`. The modules are self-contained: posture, required shape, skeletons, rewrite rules, failure modes, a verification list, and a workflow.

Module files: `references/courses/ctis151.md`, `references/courses/ctis163.md`, `references/courses/ctis164.md`, `references/courses/ctis166.md`, `references/courses/ctis255.md`, `references/courses/ctis256.md`, `references/courses/ctis259.md`, `references/courses/ctis262.md`, `references/courses/ctis264.md`, `references/courses/ctis359.md`, `references/courses/ctis411.md`, `references/courses/ctis465.md`, `references/courses/ctis474.md`.

## When invoked without a course

If the request names a course code, load that module directly. If it names only a topic, match it against the table above and say which module you chose. When work genuinely spans two courses, load both and say where the boundary falls: interface behaviour in CTIS255 against server persistence in CTIS256, requirement traceability in CTIS411 against audit evidence in CTIS474.

If nothing matches, read [shared capability primitives](references/capability-primitives.md), apply ordinary technical practice, and say that no course module was applied.

## Output contract

1. **Interpret** — restate the task, its inputs, its constraints and the artifact expected.
2. **Produce** — write the working code or artifact in the module's required shape, not a summary of it.
3. **Verify** — work through the module's verification list and report what you could not check.

The course convention governs style. An explicit user or project requirement governs over the course convention; say so when you depart.

## Boundaries

The module text is anonymous. It describes course conventions and observable teaching practice, never a named person. See the [evidence policy](references/evidence-policy.md).

Do not claim access to anyone's emotions, private thoughts, motives, diagnoses, or private communications. Where the underlying material is thin, the module says so; keep that caveat rather than presenting a guess as a course rule.

## Common mistakes

- Answering in a generic style when the course has a required shape, such as the contract comment in CTIS264 or the four STEP comments in CTIS164.
- Substituting a library call for an algorithm the task names.
- Ignoring a stated tool ban, such as the DOM API and CSS frameworks in CTIS255.
- Loading several modules for a single-course request.
- Copying assignment-specific constants, sample defects, or personal data from any source.
- Returning the artifact without the module's verification pass.
