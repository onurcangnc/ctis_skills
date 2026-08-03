# CTIS474 — Information systems auditing

You are producing an audit, not an opinion. Every statement about a control is backed by evidence you asked for and received, mapped to a standard, and rated for risk. An assertion without evidence is not a finding, and a finding without a recommendation and an owner is not finished work.

## Teaching posture

Evidence first, judgement second. Teach the chain in order: scope, risk assessment, control evaluation, fieldwork and evidence, finding, recommendation, report. Every question the auditor asks must name the standard it comes from, the evidence that would answer it, and the risk if the answer is unsatisfactory.

The work is done through case study and role play. Teams audit each other and an information systems function played by the instructor. An audit is not only fault-finding: verifying that previously agreed remediation actually happened carries the same weight.

## Scope

Governance and control frameworks, audit scope and planning, risk assessment, control evaluation, evidence collection, finding formulation, recommendations, remediation tracking, and the written audit report.

The frameworks are used by name, because the name on a finding decides which clause it is measured against: COBIT 2019 for governance and management objectives, ISO/IEC 27001 for control requirements and its Annex A clauses, ISO/IEC 27002 as the implementation guide behind those clauses, ISO 31000:2018 for the risk methodology, and ITAF for audit practice.

Business continuity and disaster recovery are in scope. The continuity plan, the backup and restore procedure, and the recovery targets are examined like any other control: the recovery time objective (RTO), how long the business can wait for recovery, and the recovery point objective (RPO), how much data loss the business will accept. A continuity gap is a finding measured against those targets, not a paragraph of concern.

## The audit chain

```text
Scope  ->  Risk assessment  ->  Control evaluation  ->  Fieldwork and evidence
       ->  Finding  ->  Recommendation  ->  Report  ->  Remediation follow-up
```

No stage may be skipped. A recommendation that arrives before evidence is a guess; a finding that arrives before the control was evaluated is an accusation.

## The question matrix

Preparation for an audit session is a table, and every row is complete before the session starts.

```text
Area        Question                                    Standard                          Expected evidence                          Risk
Patching    How is operating system patch compliance     ISO/IEC 27001 A.8.8; COBIT DSS05  Patch compliance report, last 3 cycles     High
            monitored and enforced for Linux servers?
Governance  How does the Board set the IT governance     COBIT 2019 EDM01                  Governance framework document, board      Medium
            framework and monitor whether it is applied?                                  minutes, review records
```

Four columns, always: the question, the standard it derives from, the evidence that would satisfy it, and the risk rating if it is not satisfied. The standard column holds the clause, not just the framework: `ISO/IEC 27001 A.8.8` names the annex control and `COBIT 2019 EDM01` names the governance objective. A question with no expected evidence cannot be answered conclusively, so it is not ready to ask.

Ask for records, not descriptions. "How do you handle X" invites a story; "show me the last three X reports" produces evidence.

## Choosing the framework

Each framework answers a different question, and the choice is not interchangeable:

- **COBIT 2019** for governance and management objectives. It is used when the finding is about whether a goal is set, owned, and monitored, keyed by goal codes such as `EDM01` and `DSS05`.
- **ISO/IEC 27001** for control requirements, keyed by Annex A clause references such as `A.5.9` (inventory of information and associated assets), `A.5.18` (access rights), `A.8.5` (secure authentication), and `A.8.8` (management of technical vulnerabilities).
- **ISO/IEC 27002** as the implementation guidance behind an ISO/IEC 27001 clause: it explains how to operate a control, not what is required.
- **ISO 31000:2018** for the risk methodology, aligned with COBIT `APO12`: a risk-based methodology built on it is the course pattern.
- **ITAF** for audit practice: how the engagement is planned, performed, and reported.
- **NIST** appears as a side reference in the source material; it is not used as a primary framework here.

A single finding can carry two references when both apply, as in the two lines above that pair an ISO/IEC 27001 Annex A clause with a COBIT goal code. When the framework is not named, neither is the clause, and the finding fails.

## Finding structure

```text
Finding ID:      F-IS-07
Condition:       What was observed, stated factually.
Criteria:        The standard, policy or requirement the condition is measured against.
Cause:           Why the condition exists.
Effect:          The consequence if it continues, expressed as business impact.
Evidence:        The specific artifacts examined, with dates and identifiers.
Risk rating:     High / Medium / Low, against a stated scale.
Recommendation:  A specific, assignable action.
Owner:           A named role.
Target date:     When it will be completed.
Management response: Accepted, accepted with modification, or accepted risk.
```

Condition and criteria are separate lines. Merging them produces a sentence that sounds like an opinion.

Not every issue is a control failure. An observation records a point of improvement, an emerging risk, or an area where evidence was insufficient to conclude. Classify it as an observation and say which of the three it is, rather than inflating it into a finding.

## Evidence

| Class | Example | Strength |
|---|---|---|
| Documentary | signed policy, approved charter, board minutes | strong when dated and approved |
| System-generated | patch compliance report, access review export, log extract | strongest, hard to fabricate |
| Corroborative | two independent sources agreeing | strengthens either of the above |
| Testimonial | an interview answer | weakest, needs corroboration |

Record for every item: what it was, who provided it, its date, and what it demonstrates. Evidence that predates the audit period does not support a conclusion about the period.

Where evidence could not be obtained, say so in the report and mark the conclusion as limited. Never fill a gap with an assumption.

## Remediation follow-up

Previously reported findings are re-tested and given a status:

```text
Status                   Meaning                                             Evidence required
Remediated               The control now operates as intended                Current evidence of operation
Partially Remediated     Some elements in place, cycle incomplete            What exists plus what is outstanding
Not Remediated           No effective change                                 Re-test result
Accepted Risk            Management chose not to act, with authority         Documented acceptance and approver
```

Write the status with what supports it and what is still missing. A worked example of a partial status: a policy approved in one month, a first consolidated submission the month before, and the first full cycle still pending. That is `Partially Remediated`, and the report says exactly why.

A policy that exists on paper is not a control. It becomes a control when there is evidence it operates: an incident recorded, a decision taken, a consequence applied.

## Report shape

```text
1. Executive summary            conclusion first, in business language
2. Scope and objectives         what was and was not examined, and the period
3. Approach                     how evidence was gathered
4. Findings                     in risk order, each in the structure above
5. Observations                 improvements and unconcluded areas
6. Remediation status           previously reported items and their current state
7. Points of disagreement       where management disagrees, with both positions
8. Appendices                   evidence register, question matrix
```

Points of disagreement are recorded, not resolved by the auditor. State the auditor position, the management position, and leave the reader to judge.

Order findings by risk, not by the order they were discovered.

## Rules with rewrites

**Assertion without evidence.**
"Access controls are weak" becomes the condition observed, the artifact examined, its date, and the criteria it failed.

**Condition merged with criteria.**
"The company does not patch properly" becomes a condition line stating what was observed and a criteria line naming the standard clause.

**Framework named without its clause.**
"Violates COBIT" becomes "fails to meet COBIT 2019 DSS05.04, the access rights objective". The framework name is never enough, the clause or objective must be named. Mapping a finding to a broad framework name without the applicable clause is a failure mode, not a finding.

**Effect written as a restatement.**
"The effect is that servers are unpatched" becomes the business consequence: exposure window, affected systems, regulatory or financial impact.

**Recommendation with no owner.**
"Patching should be improved" becomes a specific action, a named role, and a target date.

**Testimonial evidence treated as conclusive.**
"Management stated that reviews occur quarterly" becomes the same statement plus the review records, or an explicit note that corroboration was not obtained.

**Observation inflated into a finding.**
An area where evidence was insufficient becomes an observation, classified as such, with the missing evidence named.

**Policy counted as a control.**
"A policy exists, so the control is effective" becomes evidence that the policy operated: an incident, a decision, a consequence.

**Remediation status asserted.**
"The prior finding was fixed" becomes a status from the fixed set, with current evidence and anything still outstanding.

**Findings in discovery order.**
A list following the session order becomes a list ordered by risk rating.

**Disagreement resolved by the auditor.**
"Management is wrong about this" becomes both positions recorded under points of disagreement.

## Failure modes

- Auditing outside the agreed scope, which invalidates the finding regardless of merit.
- Evidence dated outside the audit period used to support a conclusion about the period.
- A risk rating applied with no stated scale, so High and Medium mean nothing.
- Sampling without saying how the sample was chosen or how large it was.
- Mapping a finding to a broad framework name without the applicable clause, objective, or control, so the criteria line cannot be checked.
- Recommending a specific product rather than a control outcome.
- Reporting the same underlying cause as several findings, inflating the count.
- Losing independence by advising on the design of the control you will later test.
- Treating an interview answer and a system report as equally strong.
- A findings register with no owners or deadlines, which cannot be followed up.
- Writing the executive summary as a narrative of the audit rather than the conclusion.

## Verification

Before reporting the audit as done, confirm all of these:

- Scope, period and objectives are stated, including what was excluded.
- Every question in the matrix has a standard, expected evidence and a risk rating.
- Every finding separates condition, criteria, cause and effect.
- Every finding names the evidence examined, with dates and identifiers.
- Every finding has a recommendation, a named owner and a target date.
- Risk ratings are applied against a stated scale.
- Observations are classified as improvement, emerging risk, or insufficient evidence.
- Prior findings carry a status from the fixed set with supporting evidence.
- Areas where evidence could not be obtained are declared, and the conclusion is marked limited.
- Findings are ordered by risk and the executive summary leads with the conclusion.

## Workflow

1. Agree the scope, the period and the objectives, and write down what is excluded.
2. Assess risk across the areas in scope and rank them.
3. Build the question matrix: question, standard, expected evidence, risk.
4. Conduct fieldwork and record every artifact received with its date and source.
5. Evaluate each control against its criteria and draft findings in the fixed structure.
6. Separate observations from findings and classify them.
7. Re-test prior findings and assign a remediation status.
8. Write the report with the conclusion first and findings in risk order.
9. Report which areas you could not conclude on and why.
