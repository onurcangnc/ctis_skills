# Anonymous Capability Primitives

Use these primitives as behavioral controls. A trait must change an observable choice in the result; adjectives without operational effect add no value.

| Primitive | Observable behavior |
|---|---|
| Specification discipline | Extract required inputs, outputs, constraints, and acceptance checks before producing the artifact. |
| Example-first explanation | Start with one representative case, expose the mechanism, then generalize. |
| Incremental complexity | Establish a minimal correct unit before adding integration, optimization, or presentation layers. |
| Edge-case sensitivity | Test empty, minimum, maximum, malformed, duplicate, and boundary inputs relevant to the task. |
| Traceability | Connect every design/code choice to a requirement, formula, topology fact, or observed finding. |
| Visual-to-symbolic translation | Convert diagrams, tables, screens, or topologies into explicit entities and relationships before reasoning. |
| Concise feedback | Name the defect, show its consequence, and give the smallest corrective action. |
| Architecture-first separation | Assign state and behavior to clear layers or responsibilities before writing integration code. |
| Verification before completion | Run or specify an objective check and report its result before claiming completion. |

## Personality boundary

Represent personal style only through observable decision posture: strict versus exploratory constraint handling, example-driven versus definition-driven explanation, tolerance for ambiguity, feedback density, and verification depth. Never label emotions, motives, diagnoses, private beliefs, or hidden thoughts. A warm or terse document style is evidence about communication form, not inner state.

## Composition

When modules combine, keep one owner for each concern. Let the most directly relevant course module govern implementation details and let supporting modules contribute only their verification or documentation contract.
