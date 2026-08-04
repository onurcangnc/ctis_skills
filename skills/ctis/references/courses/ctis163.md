# CTIS163 — Discrete Mathematics

You are answering a mathematics question, not writing a program. The answer is a claim plus the argument that settles it. A true universal statement needs a proof over the whole domain; a false one needs a single counterexample. Getting the right verdict with the wrong kind of argument earns nothing.

Evidence note: this module is derived from one student's collected material for a single section in a single term. The conventions it states recur across that material and are reliable. What varies by section, instructor or term is not established by it: grading weights, submission mechanics, and which topics an exam covers should be asked for rather than assumed.

## Teaching posture

Definition first, then representation, then example, then the boundary case. State which definition you are applying before you apply it. When a statement is false, name the witness that breaks it and show the predicate failing at that value. Keep the answer in the shape the course uses: the question, then `Solution:`, then a one-sentence verdict with its reason.

Disproving is not the mirror image of proving. Say which of the two you are doing before you start.

## Scope

Predicate logic, universal and existential quantifiers, nested quantifiers and their order, negation with the generalized De Morgan laws, functions and their representations, one-to-one and onto properties, relations, digraphs, relation matrices, composition by matrix product, and property checks such as reflexivity, symmetry, and transitivity.

## The answer shape

```text
Statement:  ∀x P(x), domain R
Solution:   The statement is false.
            Take x = 1/2.
            Then P(1/2) is false because ... .
            Therefore ∀x P(x) is false.
```

Four moves, always in this order: restate with the domain, give the verdict, produce the witness or the general argument, close with "Therefore".

## The four quantifier duties

| Statement | To prove it true | To prove it false |
|---|---|---|
| `∀x P(x)` | argue `P(x)` holds for an arbitrary `x` in the domain | one counterexample |
| `∃x P(x)` | one witness | argue `P(x)` fails for every `x` in the domain |

Two of these four take a single value, two take a general argument. Choosing the wrong column is the most common error in the whole course.

A worked pair:

```text
∃n (n prime → n+1, n+2, n+3, n+4 all not prime), domain Z+
Solution: True. Take n = 23. 23 is prime, and 24, 25, 26, 27 are all composite.
          Therefore the statement is true.

∀x (x² ≥ x), domain R
Solution: False. Take x = 1/2. Then x² = 1/4 and 1/4 ≥ 1/2 is false.
          Therefore the statement is false.
```

## Nested quantifiers

Order changes the meaning. Read left to right and treat each quantifier as a move in a game: `∀` is the opponent choosing, `∃` is you answering. You may use everything chosen before you.

```text
∀x∃y (x + y = 0), domain R × R
Solution: True. Let x be arbitrary. Choose y = -x. Then x + y = 0.
          The choice of y is allowed to depend on x.
          Therefore the statement is true.

∃x∀y (x + y = 0), domain R × R
Solution: False. One x would have to work for every y.
          Fix any x. Take y = 1 - x. Then x + y = 1 ≠ 0.
          Therefore the statement is false.
```

Same predicate, opposite verdicts. Whenever both quantifiers appear, say explicitly whether the inner choice may depend on the outer one.

Translating between words and symbols, with `L(x, y)` meaning "x loves y":

| Sentence | Symbolic |
|---|---|
| Everybody loves somebody | `∀x∃y L(x, y)` |
| There is a person who loves everybody | `∃x∀y L(x, y)` |
| Somebody loves somebody | `∃x∃y L(x, y)` |
| For every integer m there is a larger integer n | `∀m∃n (m < n)`, domain `Z` |

Read the symbolic form back into words before accepting it. "Everybody loves somebody" and "somebody is loved by everybody" are different statements.

## Negation

Push the negation inward one symbol at a time. Each `∀` becomes `∃`, each `∃` becomes `∀`, and the inner predicate is negated.

```text
¬∀x P(x)  ≡  ∃x ¬P(x)
¬∃x P(x)  ≡  ∀x ¬P(x)
¬(A ∧ B)  ≡  ¬A ∨ ¬B
¬(A ∨ B)  ≡  ¬A ∧ ¬B
¬(A → B)  ≡  A ∧ ¬B
```

Worked step by step, never in one jump:

```text
¬∀x∃y (P(x,y) ∧ Q(y))
≡ ∃x ¬∃y (P(x,y) ∧ Q(y))
≡ ∃x ∀y ¬(P(x,y) ∧ Q(y))
≡ ∃x ∀y (¬P(x,y) ∨ ¬Q(y))
```

The conditional case is the one people get wrong: negating "if A then B" gives "A and not B", not "if A then not B".

## Functions

A function `f` from `X` to `Y` maps every element of `X` to exactly one element of `Y`. In an arrow diagram that means exactly one arrow leaves each element of `X`. Three representations of the same object:

| Form | Example |
|---|---|
| List of ordered pairs | `f = {(a,1), (b,3), (c,2), (d,1)}` |
| Formula | `f = {(n, n+2) | n is a positive integer}`, or `f(n) = n + 2` |
| Values | `f(a) = 1`, `f(b) = 3`, `f(c) = 2` |

Plus the arrow diagram. When a question gives one form, produce the others; the representation shift is usually where the answer becomes obvious.

Properties, each with its own proof shape:

```text
One-to-one (injective): assume f(a) = f(b), derive a = b.
    f(x) = 3x + 5.  Assume 3a + 5 = 3b + 5.  Then 3a = 3b, so a = b.  Injective.

Not one-to-one: exhibit a ≠ b with f(a) = f(b).
    f = {(a,1), (b,3), (c,2), (d,1)}.  a ≠ d but f(a) = f(d) = 1.  Not injective.

Onto (surjective): take an arbitrary y in the codomain, construct an x with f(x) = y.
```

Two named functions the course uses: the sign function `sgn(x)`, which is `-1`, `0`, or `1` according to the sign of `x` and satisfies `x = sgn(x) · |x|`; and the linear congruential recurrence for pseudorandom numbers, `x_n = (a · x_{n-1} + c) mod m`, generated by iterating from a seed `x_0`.

## Relations

A relation `R` on a set `X` is a set of ordered pairs from `X × X`. Three representations again: the pair list, the digraph, and the matrix.

```text
X = {a, b, c, d}
R = {(a,a), (b,c), (c,b), (d,d)}

Digraph: a loop at a, a loop at d, an arrow b→c and an arrow c→b.

Matrix (rows and columns in the order a, b, c, d; entry 1 when the pair is in R):
        a b c d
    a [ 1 0 0 0 ]
    b [ 0 0 1 0 ]
    c [ 0 1 0 0 ]
    d [ 0 0 0 1 ]
```

Property checks, each read directly off one of the three forms:

| Property | Definition | Read it from |
|---|---|---|
| Reflexive | `(x,x) ∈ R` for every `x ∈ X` | a loop at every vertex; all-ones diagonal |
| Symmetric | `(x,y) ∈ R` implies `(y,x) ∈ R` | every arrow has its reverse; matrix equals its transpose |
| Antisymmetric | `(x,y) ∈ R` and `(y,x) ∈ R` imply `x = y` | no two-way arrow between distinct vertices |
| Transitive | `(x,y) ∈ R` and `(y,z) ∈ R` imply `(x,z) ∈ R` | wherever a two-step path exists, the direct arrow exists |

For the example above: not reflexive, because `(b,b) ∉ R`. Symmetric, because the only asymmetric candidates `(b,c)` and `(c,b)` are both present.

Transitivity has a mechanical check. Compute `A²` as a Boolean matrix product: entry `(i,j)` is 1 when some `k` gives `A[i][k] = 1` and `A[k][j] = 1`, that is, when a two-step path exists. The relation is transitive exactly when every 1 in `A²` is also a 1 in `A`.

```text
If A²[i][j] = 1 and A[i][j] = 0, then (i,j) breaks transitivity.
Report that pair as the counterexample.
```

The same Boolean product computes composition: `R ∘ S` has matrix `A_S · A_R` under Boolean arithmetic, where addition is OR and multiplication is AND.

## Rules with rewrites

**Disproving a universal with an argument instead of a witness.**
"In general x² is not always at least x" becomes "Take x = 1/2; then 1/4 ≥ 1/2 is false."

**Proving an existential with a general argument.**
"Some integer must satisfy it" becomes a named witness and the predicate evaluated at it.

**Proving a universal with an example.**
"For x = 3 it holds, so the statement is true" becomes an argument for an arbitrary element of the domain.

**Dropping the domain.**
`∀x (x² ≥ x)` becomes `∀x (x² ≥ x)` over `R`, with the domain stated. The verdict changes over `Z`, where it is true.

**Swapping nested quantifiers.**
Treating `∀x∃y` and `∃x∀y` as equivalent becomes two separate evaluations, with a sentence saying whether the inner choice may depend on the outer one.

**Negating a conditional as a conditional.**
`¬(A → B) ≡ (A → ¬B)` becomes `¬(A → B) ≡ A ∧ ¬B`.

**Negating in one jump.**
A single rewritten line becomes the chain of steps, one quantifier or connective per line.

**Calling a relation transitive after checking one triple.**
One verified triple becomes the `A²` check, or an explicit argument over all pairs.

**Confusing symmetric with antisymmetric.**
Both being asserted at once becomes a check against the definitions; a relation can be both only when it has no two-way arrow between distinct elements.

**Answering with a verdict alone.**
"False" becomes "False, because ... . Therefore the statement is false."

## Failure modes

- Using a counterexample against an existential statement, where it proves nothing.
- Assuming the arbitrary element has a convenient property that the domain does not guarantee.
- Reading `∀x∃y` as "one y works for all x".
- Forgetting that an empty domain makes every universal statement vacuously true.
- Mixing up the direction of a pair: `(x,y)` means x relates to y, and the digraph arrow points from x to y.
- Building the relation matrix with rows and columns in different orders.
- Treating `A²` as ordinary matrix multiplication and reporting entry values above 1 instead of Boolean 1s.
- Calling a relation reflexive after checking a loop on some vertices rather than all.
- Treating "no arrow either way" as a violation of symmetry; symmetry only constrains pairs already in the relation.
- Declaring a mapping a function when one element of the domain has two arrows, or none.

## Verification

Before reporting the answer as done, confirm all of these:

- The domain is stated, and the argument stays inside it.
- The verdict matches the argument type: witness for a true existential or a false universal, general argument for the other two.
- Every quantifier in a nested statement is handled in left-to-right order, with dependence stated.
- Negations were pushed inward one symbol at a time, with the conditional case expanded correctly.
- Any claimed property of a relation was checked against its definition over all required pairs, not a sample.
- A transitivity claim is backed by the `A²` comparison or an explicit argument.
- The answer ends with a "Therefore" sentence that names the original statement.

## Workflow

1. Restate the statement symbolically and write down the domain.
2. Decide whether you are proving or disproving, and name which of the four duties applies.
3. Choose the representation that makes the work easiest: pairs, formula, diagram, or matrix.
4. Produce the witness or the general argument, showing the predicate evaluated at the critical value.
5. For relations, check each property against its definition and use `A²` for transitivity.
6. Close with the "Therefore" sentence.
7. State any step you could not fully justify.
