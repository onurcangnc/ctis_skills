# CTIS359 — Software engineering: estimation, quality, and test coverage

This course has two distinct bodies of work, taught in different styles. Estimation and quality are measurement subjects, answered with a counted table and a formula. Coverage and testing are analysis subjects, answered with a control-flow graph and a test-case table. Decide which one the question belongs to before answering, because the shape of a good answer is different.

Evidence note: this module is derived from one student's collected material for a single section in a single term. The conventions it states recur across that material and are reliable. What varies by section, instructor or term is not established by it: grading weights, submission mechanics, and which topics an exam covers should be asked for rather than assumed.

## Teaching posture

**On the measurement side:** agenda, taxonomy, method, formula, worked example. Every method is presented with its advantages and disadvantages side by side rather than ranked. Show the arithmetic step by step, and cite the standard or manual the counting rule comes from.

**On the analysis side:** definition, rule, code example with line numbers, then the boundary case where the rule is not enough, then one more test case that closes the gap. Never present a coverage criterion without showing what it fails to catch.

Ask the framing question before giving a definition when the concept is contested. Quality has no single definition; whose quality, for what purpose, is the first thing to settle.

## Scope

Software size and cost estimation, function point analysis, COCOMO, non-algorithmic estimation methods, software quality models and their limits, control-flow graphs, and the coverage criteria up to MC/DC.

## Function point analysis

Count first, adjust second. The two stages are separate and both must be shown.

**Stage 1: unadjusted function points.** Classify every function into one of five types, assign complexity, and read the weight from the IFPUG table.

| Type | Meaning | Boundary test |
|---|---|---|
| EI, external input | data entering to maintain an internal file | crosses the boundary inwards |
| EO, external output | derived data leaving the application | leaves and involves processing |
| EQ, external inquiry | retrieval with no derived data | leaves without calculation |
| ILF, internal logical file | data group maintained inside the boundary | maintained by the application |
| EIF, external interface file | data group referenced but not maintained | maintained elsewhere |

The application boundary decides every classification. Draw it before counting, and state where it sits.

```text
Function                    Type   DET  RET/FTR  Complexity  Weight
Create company contact      EI     12   2        Average     4
List contacts               EQ      8   1        Low         3
...
                                              Unadjusted FP =  31
```

**Stage 2: the value adjustment factor.** Rate the fourteen general system characteristics from 0 to 5, total them as the total degree of influence, and apply:

```text
VAF = 0.65 + (0.01 × TDI)
FP  = UFP × VAF

Example: UFP = 31, TDI = 40
         VAF = 0.65 + 0.40 = 1.05
         FP  = 31 × 1.05 = 32.55
```

Report both numbers. An answer that gives only the adjusted total hides where the count came from.

Three count types exist and they are not interchangeable: a development count for a project, an application count for what is delivered and running, and an enhancement count for a change to existing software.

## Cost estimation

Classify the method before applying it.

| Family | Methods | Strength | Weakness |
|---|---|---|---|
| Algorithmic | COCOMO, function points | repeatable, auditable | needs calibration data |
| Expert judgement | one or several experts | fast, uses experience | unrepeatable, biased |
| Estimation by analogy | compare with a finished project | grounded in reality | needs a similar project |
| Parkinson | effort equals available resource | trivial | not an estimate |
| Pricing to win | effort equals the customer's budget | wins the bid | unrelated to the work |
| Top-down | from the whole to the parts | early, cheap | misses component detail |
| Bottom-up | from the parts to the whole | detailed | misses integration cost |

Every method gets its advantages and its disadvantages. Naming only the strengths is an incomplete answer.

Intermediate COCOMO, worked in the order the course uses:

```text
1. Nominal effort:  E_nom = a × (KLOC ^ b)
2. Effort adjustment factor: EAF = product of the 15 cost driver ratings
3. Adjusted effort:  E = E_nom × EAF                  person-months
4. Schedule:         D = c × (E ^ d)                  months
5. Staffing:         N = E / D                        people
```

Write the coefficients you used for the mode (organic, semi-detached, embedded), then substitute, then compute. Keep the units on every line.

## Quality

Quality is not one property and the course does not treat it as one. Start from the stakeholder: the user, the developer, the buyer and the maintainer want different things, and a model that satisfies one can fail another.

Answer a quality question in three moves: whose view, which attributes, how each attribute would be measured. Name the limitation of the model you chose. There is no definitive quality model, and saying so with a reason is part of a correct answer.

Beyond a certain point, raising an attribute raises cost. Say where that trade-off falls rather than treating more quality as always better.

## Control-flow graphs

Number the statements, then draw one node per statement or basic block and one edge per possible transfer.

```java
1  public int classify(int a, int b) {
2      int result = 0;
3      if (a > 0 && b > 0) {
4          result = a + b;
5      } else {
6          result = -1;
7      }
8      return result;
9  }
```

```text
        (1,2)
          |
         (3)
        /   \
     (4)     (6)
        \   /
        (8,9)
```

Each structure has a fixed graph shape: a sequence is a chain, `if` splits and rejoins, `if-else` splits into two branches that rejoin, `while` tests before the body and loops back, `do-while` loops back before the test, `for` is a while with initialisation and update attached, and a `switch` fans out with one edge per case plus one for the default.

## Coverage criteria

Each criterion is stronger than the one above it, and each is introduced by showing what the previous one misses.

| Criterion | Satisfied when | Misses |
|---|---|---|
| Line | every line executed at least once | two statements on one line, so one runs and the line looks covered |
| Statement | every statement executed | a branch never taken because it has no statement |
| Branch, decision | every decision outcome taken both ways | the individual conditions inside a compound decision |
| Condition | every atomic condition true and false | the decision outcome itself |
| Condition/decision | both of the above | interaction between conditions |
| MC/DC | each condition shown to independently affect the outcome | most, at a cost of n+1 tests |

The line-coverage limitation is the one the course keeps returning to. When an `if` and its consequence sit on the same line, executing the line does not prove the consequence ran. Write the two statements on separate lines before measuring, or measure statements instead.

**MC/DC, worked.** For the decision `(a > 0 && b > 0)`, find for each condition a pair of test cases that differ in that condition alone and produce different outcomes.

```text
#  a>0    b>0    decision
1  true   true   true
2  false  true   false      pair with 1 -> a is independently shown
3  true   false  false      pair with 1 -> b is independently shown
```

Three tests for two conditions. Present the table, then name the pair that proves each condition, then state the coverage reached.

The standard exercise pattern is progressive: measure the coverage of the current suite, name the gap, add one more test case, and show the criterion is now satisfied.

## Rules with rewrites

**Counting function points without a boundary.**
A count that starts from a feature list becomes one that starts with the application boundary drawn and stated.

**Reporting only the adjusted total.**
`FP = 32.55` becomes the unadjusted count, the TDI, the VAF calculation, and then the adjusted total.

**Method named without its weakness.**
"Use expert judgement" becomes the method with its advantage and its disadvantage stated together.

**COCOMO applied without a mode.**
`E = 2.4 × KLOC^1.05` becomes the same with the mode named and the coefficients justified.

**Effort reported without units.**
`E = 45` becomes `E = 45 person-months`.

**Quality asserted absolutely.**
"The system is high quality" becomes the stakeholder, the attributes, and how each would be measured.

**Coverage claimed from a run.**
"All lines ran, so it is tested" becomes the criterion named, the graph, and the gap the criterion leaves.

**Compound decision tested once.**
One test through `a > 0 && b > 0` becomes the MC/DC table showing each condition independently affecting the outcome.

**Graph drawn without numbered code.**
An unlabelled diagram becomes a graph whose nodes carry the statement numbers they represent.

## Failure modes

- Classifying a retrieval that performs a calculation as an inquiry rather than an output.
- Counting a referenced file as internal because the application reads it.
- Applying the VAF twice, or adding it instead of multiplying.
- Using the nominal effort in the schedule formula instead of the adjusted effort.
- Treating pricing to win or Parkinson as estimation methods rather than as pricing behaviours.
- Drawing a `while` graph with the test after the body.
- Forgetting the implicit `else` edge when an `if` has no else branch.
- Claiming MC/DC from a pair that differs in two conditions at once.
- Assuming branch coverage implies condition coverage; neither implies the other.
- Presenting a quality model as definitive.

## Verification

Before reporting the answer as done, confirm all of these:

- The question was assigned to the measurement side or the analysis side, and answered in that shape.
- For a count: the boundary is stated, every function is classified with its type and complexity, and both the unadjusted and adjusted totals appear.
- For an estimate: the method family is named, the formula is written before substitution, and every result carries its unit.
- Every method mentioned carries both an advantage and a disadvantage.
- For a graph: the code is numbered and every node maps to a numbered statement.
- For coverage: the criterion is named, the test table is shown, and the remaining gap is stated.
- An MC/DC claim identifies the specific pair proving each condition.
- Sources are named where the counting rule or the model came from.

## Workflow

1. Decide which body the question belongs to and say so.
2. For measurement: draw the boundary or name the mode, then build the table, then apply the formula.
3. For analysis: number the code, draw the graph, then build the test table.
4. Show the arithmetic step by step, with units.
5. Name the limitation of the method or criterion you used.
6. For coverage exercises, add the test case that closes the gap and restate the coverage reached.
7. Report what you computed and any input you had to assume.
