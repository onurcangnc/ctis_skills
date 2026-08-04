# CTIS411 — Project documentation and requirements

The deliverable is a document, and the document is a controlled artifact. Sections are fixed, every requirement carries an identifier, every change is recorded, and every team member's contribution is named. A well-written paragraph in the wrong section, or a requirement with no identifier, fails for a reason that has nothing to do with the writing.

Evidence note: this module is derived from one student's collected material for a single section in a single term. The conventions it states recur across that material and are reliable. What varies by section, instructor or term is not established by it: grading weights, submission mechanics, and which topics an exam covers should be asked for rather than assumed.

## Teaching posture

Give the template first, then fill it. Every section exists to answer one question, so name that question before writing the section. Requirements are the backbone: everything downstream, from the work breakdown to the test plan, traces back to a numbered requirement. Teach the identifier scheme early, because retro-fitting it across a finished document is painful.

Roles are real. Each team member owns named sections and is accountable for them in the contribution table.

## Scope

Software project management plans (SPMP), initial plans, requirement specification (SRS), functional and non-functional requirements, work breakdown structures, milestones and deliverables, stakeholder analysis, communication plans, change control, risk registers, traceability, and the branch-and-merge workflow used to produce the documents.

The process model is part of the scope and it is named: the course uses the Scrum software development process model, and the plan justifies it for the project at hand. The deliverables that carry the grade are the SPMP and the Initial Plan; the SRS is the requirements artifact the plan traces to. Scrum artifacts (backlogs, issues, milestones) are managed on the version control platform, so the plan, the issues and the documents resolve to the same project.

## The required document skeleton

These sections are mandatory. Keep the names and the order.

```text
Change History              version, date, author, summary of change
Executive Summary
Individual Contributions    member -> sections owned
Product Requirements        functional and non-functional, each with an id
Process Model               which model, why this project, and how it was customized
Work Breakdown Structure    tasks decomposed to assignable units
Milestones and Deliverables date, artifact, acceptance
Stakeholders                who, interest, influence, expectation
Communication Plan          what, to whom, how often, through which channel
Change Control              who requests, who approves, how it is recorded
Risks                       id, description, probability, impact, mitigation, owner
```

Every section is filled or explicitly marked as not applicable with a reason. An empty heading is worse than an absent one.

## Skeletons

### Requirement identifiers

Number functional and non-functional requirements in separate sequences, and never renumber. A retired requirement is marked withdrawn, not deleted, so earlier references stay valid.

```text
FReq1: User Registration and Wardrobe Creation
    Users create accounts and build a personal digital wardrobe by uploading
    photographs of clothing items. The system removes image backgrounds and
    categorises items by type.
    Priority: Must have
    Source: Client interview, 12 March
    Acceptance: A registered user uploads a photograph and sees the item
                listed under a category within 10 seconds.

NFReq3: Usability
    A non-technical user completes wardrobe upload, outfit suggestion and
    community browsing without training.
    Measure: 8 of 10 first-time users complete all three tasks unaided
             in under 5 minutes.
```

A non-functional requirement without a measure is an opinion. "Fast", "user-friendly" and "secure" are not requirements until a number or a testable condition is attached.

### Work breakdown structure

Decompose until each leaf is a task one person can be assigned and can be called done. Number the levels so the structure is visible in the identifier.

```text
1   Wardrobe module
1.1     Image upload
1.1.1       Upload form and validation          FReq1   3 days   member A
1.1.2       Background removal integration      FReq1   5 days   member B
1.2     Categorisation
1.2.1       Category model                      FReq1   2 days   member A
```

Every leaf carries the requirement it serves. A task with no requirement means either the task is unnecessary or a requirement is missing.

### Traceability

The table is the point of the course. It is read in both directions: forwards to see whether a requirement was built and tested, backwards to see why a component exists.

```text
Requirement  Design element   Component        Test case   Status
FReq1        Wardrobe module  UploadService    TC-01,TC-02 Verified
FReq2        Outfit engine    SuggestionEngine TC-05       In progress
NFReq3       UI layer         all screens      TC-11       Not started
```

A requirement with no test case, or a test case with no requirement, is a defect in the document.

### Stakeholders

State the role, what they want, and how much influence they hold. Include the academic stakeholder explicitly.

```text
Stakeholder   Interest                          Influence  Expectation
Client        A working wardrobe application    High       Weekly demonstration
End users     Ease of use                       Medium     Usable without training
Instructor    Documentation compliance and      High       Sections complete, on time,
              academic assessment                          graded against course rules
Team members  Fair workload, clear ownership    Medium     Contributions recorded
```

### Risk register

```text
Id    Risk                              P    I    Exposure  Mitigation                        Owner
R-01  Background removal API rate limit M    H    High      Cache results, add a fallback     member B
R-02  Team member unavailable in exams  H    M    High      Pair on every module, share docs  member C
```

Probability and impact are rated on a stated scale, not left as adjectives. Every risk has one named owner. A risk with no mitigation and no owner is a note, not a risk entry.

### Change control and the branch workflow

Documents are versioned like code, and the workflow is part of the deliverable.

```text
1. Create a new branch from main for the required changes.
2. Implement and commit the changes in that branch.
3. Submit a merge request to merge the branch into test.
4. Record the change in the Change History table with version, date, author and summary.
```

The Change History table is updated in the same merge request as the change it describes. A document whose history stops before its last edit has lost its audit trail.

Scrum artifacts live on the same platform as the documents. The product backlog, the issues and the milestones are tracked in the version control platform's issue and milestone tools, so a requirement's status and the change that closed it are one click apart. When the Process Model says Scrum, the backlog and the issues are evidence of the model operating, not a separate tool.

## Rules with rewrites

**Requirement with no identifier.**
"The system should let users upload photos" becomes `FReq1: ...` with a priority, a source and an acceptance condition.

**Unmeasurable non-functional requirement.**
"The interface must be user-friendly" becomes a completion rate, a task, a time limit and a user group.

**Requirement stating a solution.**
"The system shall use a PostgreSQL database" becomes a requirement about the data that must be retained, with the database recorded as a design decision instead.

**Compound requirement.**
"Users can register, upload items and share outfits" becomes three numbered requirements, each independently testable.

**Task with no owner or estimate.**
`1.1.1 Upload form` becomes the same task with the requirement it serves, a duration and a named member.

**Risk without a rating.**
"There is a risk the API fails" becomes an entry with probability, impact, exposure, mitigation and owner.

**Stakeholder listed without an interest.**
`Instructor` alone becomes the role, the interest, the influence and the expectation.

**Change made without a history entry.**
A merged edit becomes a merge that also adds a Change History row.

**Contributions written as a summary.**
"Everyone contributed equally" becomes a table mapping each member to the sections they own.

**Empty mandatory section.**
A heading with no content becomes either the content or an explicit statement that it does not apply, with the reason.

## Failure modes

- Renumbering requirements after a review, which silently breaks every earlier reference.
- A traceability table built once and never updated, so it certifies a state that no longer exists.
- Work breakdown items that mirror the document sections rather than the product.
- Milestones with a date but no acceptance condition, so nobody can say whether they were met.
- A risk register listing only technical risks, with no team or schedule risks.
- Confusing a deliverable with a milestone: the deliverable is the artifact, the milestone is the point in time.
- Merging directly into the protected branch instead of raising a merge request.
- Formatting drift between sections written by different members, which the document owner is responsible for.
- Acceptance criteria written as restatements of the requirement rather than as observable conditions.

## Verification

Before reporting the document as done, confirm all of these:

- Every mandatory section is present and filled, or marked not applicable with a reason.
- Every requirement has a unique identifier, a priority, a source and an acceptance condition.
- Every non-functional requirement carries a measure.
- Every work breakdown leaf names its requirement, its estimate and its owner.
- The traceability table covers every requirement and every test case, in both directions.
- Every risk has a probability, an impact, a mitigation and a single named owner.
- The Change History records the current version, and the contribution table names section owners.
- Formatting is consistent across sections.
- The change reached the target branch through a merge request.

## Workflow

1. Start from the template and list the sections you must fill.
2. Write the requirements first, with identifiers, and get them agreed before anything downstream.
3. Derive the work breakdown from the requirements, one leaf per assignable task.
4. Build the traceability table as you go, not at the end.
5. Fill stakeholders, communication, change control and risks.
6. Assign section ownership and record it in the contribution table.
7. Branch, edit, update the Change History, and open the merge request.
8. Report which sections are complete and which are still open, with the reason.
