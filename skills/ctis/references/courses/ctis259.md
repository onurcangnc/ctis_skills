# CTIS259 — Databases with Oracle SQL

You are writing Oracle SQL against the HR sample schema. The dialect matters: this course uses `||` for concatenation, the `q'[...]'` quoting operator, `NVL`, `DECODE`, and Oracle date literals. A query that would run on another engine but not on Oracle is not an answer here.

Evidence note: the material available for this course is a student's own study notes rather than instructor handouts. The dialect, the schema and the exercise style below are taken from those notes and are reliable; grading rules, submission format and lab structure are not documented and should be asked for rather than assumed.

## Teaching posture

Work exercise by exercise from a stated question in plain language. Write the question, then the query, then the expected result shape. Introduce one clause at a time and layer them in the order they execute. When two forms produce the same result, show both and say when each is preferred.

Read the question for its output columns first. Half of the errors in this course come from answering a different question than the one asked.

## Scope

`SELECT` with projection and aliasing, string concatenation, filtering, sorting, removing duplicates, single-row functions, conditional expressions, aggregate functions with grouping, joins, subqueries, and DDL with constraints and defaults.

## The tables

The HR schema, used throughout: `employees` (`employee_id`, `first_name`, `last_name`, `salary`, `job_id`, `hire_date`, `manager_id`, `department_id`), `departments` (`department_id`, `department_name`, `manager_id`, `location_id`), `locations` (`location_id`, `city`, `state_province`), `jobs`.

## Clause order versus execution order

Written order:

```sql
SELECT   ...
FROM     ...
WHERE    ...
GROUP BY ...
HAVING   ...
ORDER BY ...
```

Execution order is `FROM`, `WHERE`, `GROUP BY`, `HAVING`, `SELECT`, `ORDER BY`. Two consequences to keep in mind at all times: a column alias defined in `SELECT` cannot be used in `WHERE`, because `WHERE` runs first; and an alias can be used in `ORDER BY`, because that runs last.

## Skeletons

### Projection, concatenation and aliases

```sql
SELECT first_name || ' ' || last_name AS "Employee Info"
FROM   employees;

SELECT first_name || ' is a ' || job_id AS "Employee Detailed Info"
FROM   employees;
```

`||` joins strings. A double-quoted alias preserves spaces and case; without the quotes Oracle folds the name to upper case.

When the literal itself contains a single quote, use the quoting operator rather than doubling the quote:

```sql
SELECT department_name || q'[ Department's manager id is ]' || manager_id
FROM   departments;
```

Any delimiter may follow `q`; the characters between the delimiters are taken literally.

### Filtering

```sql
SELECT first_name, job_id, department_id
FROM   employees
WHERE  department_id = 90;

SELECT first_name, last_name, salary
FROM   employees
WHERE  last_name = 'Whalen';           -- string literals are case sensitive

SELECT first_name, last_name, salary
FROM   employees
WHERE  last_name <> 'King';            -- <> and != are equivalent

SELECT first_name, salary
FROM   employees
WHERE  salary BETWEEN 2000 AND 3000;   -- inclusive at both ends

SELECT first_name, last_name, hire_date
FROM   employees
WHERE  hire_date = '17-FEB-96';
```

`BETWEEN` includes both endpoints. `IN` replaces a chain of `OR`. `LIKE` uses `%` for any run of characters and `_` for exactly one.

`NULL` never satisfies `=`. Test it with `IS NULL` or `IS NOT NULL`, and remember that `WHERE commission_pct <> 0.2` excludes the rows where it is null.

### Ordering and duplicates

```sql
SELECT DISTINCT department_id
FROM   employees
ORDER  BY department_id;

SELECT first_name, salary
FROM   employees
ORDER  BY salary DESC, first_name;      -- second key breaks ties
```

`DISTINCT` applies to the whole select list, not to one column. Default sort is ascending; `NULLS LAST` controls where nulls land.

### Single-row functions

```sql
SELECT UPPER(last_name), LOWER(job_id), INITCAP(first_name),
       LENGTH(last_name), SUBSTR(job_id, 1, 2), ROUND(salary / 30, 2)
FROM   employees;

SELECT last_name, TO_CHAR(hire_date, 'DD-MON-YYYY') AS hired,
       MONTHS_BETWEEN(SYSDATE, hire_date) AS months_worked
FROM   employees;
```

Format the date on output with `TO_CHAR`, and parse an ambiguous input with `TO_DATE('17/02/1996', 'DD/MM/YYYY')` rather than relying on the session format.

### Handling nulls and conditions

```sql
SELECT last_name, salary, NVL(commission_pct, 0) AS commission
FROM   employees;

SELECT last_name, NVL2(commission_pct, 'Commissioned', 'Salaried') AS pay_type
FROM   employees;

SELECT last_name, salary,
       CASE WHEN salary <  5000 THEN 'Low'
            WHEN salary < 10000 THEN 'Medium'
            ELSE 'High'
       END AS band
FROM   employees;

SELECT last_name, DECODE(department_id, 10, 'Admin', 20, 'Marketing', 'Other') AS dept
FROM   employees;
```

`NVL` substitutes for null, `NVL2` chooses between two values by nullness, `CASE` handles ranges, `DECODE` handles equality against a list. These appear in the select list, not in `WHERE`.

Any arithmetic involving a null yields null, so `salary + commission_pct` is null for uncommissioned employees. Wrap the nullable operand in `NVL` before computing.

### Aggregates and grouping

```sql
SELECT   department_id, MAX(salary)
FROM     employees
GROUP BY department_id
HAVING   MAX(salary) > 10000;

SELECT   job_id, SUM(salary)
FROM     employees
WHERE    job_id NOT LIKE '%REP%'
GROUP BY job_id
HAVING   SUM(salary) > 13000;
```

Every non-aggregated column in `SELECT` must appear in `GROUP BY`. Filter rows with `WHERE` before grouping and filter groups with `HAVING` after; putting an aggregate in `WHERE` is an error, and putting a plain row condition in `HAVING` works but scans more than it needs to.

`COUNT(*)` counts rows including nulls; `COUNT(column)` skips nulls. `AVG` also skips nulls, so `AVG(commission_pct)` divides by the commissioned employees only.

### Joins

```sql
-- natural join: requires exactly one common column name
SELECT department_name, city
FROM   departments
NATURAL JOIN locations;

-- explicit join condition, the safe default
SELECT e.first_name, e.last_name, d.department_name
FROM   employees e
JOIN   departments d ON e.department_id = d.department_id;

-- keep employees with no department
SELECT e.last_name, d.department_name
FROM   employees e
LEFT JOIN departments d ON e.department_id = d.department_id;

-- self join: each employee with their manager
SELECT w.last_name AS worker, m.last_name AS manager
FROM   employees w
JOIN   employees m ON w.manager_id = m.employee_id;
```

`NATURAL JOIN` matches on every identically named column, which silently changes meaning when a second shared name exists. Prefer an explicit `ON`. A self join always needs two aliases.

Omitting the join condition produces a Cartesian product: every row of one table against every row of the other.

### Subqueries

```sql
SELECT last_name, salary
FROM   employees
WHERE  salary > (SELECT AVG(salary) FROM employees);

SELECT last_name
FROM   employees
WHERE  department_id IN (SELECT department_id FROM departments WHERE location_id = 1700);
```

A single-row subquery goes with `=`, `>`, `<`. A multi-row subquery needs `IN`, `ANY` or `ALL`. Using `=` against a subquery that returns several rows raises an error at run time.

### DDL

```sql
CREATE TABLE hire_dates (
    id        NUMBER(8)     PRIMARY KEY,
    hire_date DATE          DEFAULT SYSDATE,
    title     VARCHAR2(50)  NOT NULL,
    dept_id   NUMBER(4)     REFERENCES departments(department_id),
    CONSTRAINT chk_title CHECK (title = UPPER(title))
);
```

A default value may be a literal, an expression or a function such as `SYSDATE`, and its type must match the column. Another column name or a pseudocolumn is not a legal default. Name the constraints; a system-generated name is unreadable when the violation is reported.

## Rules with rewrites

**Concatenating with `+`.**
`first_name + ' ' + last_name` becomes `first_name || ' ' || last_name`.

**Alias used in WHERE.**
`WHERE annual > 60000` with `salary * 12 AS annual` becomes `WHERE salary * 12 > 60000`.

**Null compared with equality.**
`WHERE commission_pct = NULL` becomes `WHERE commission_pct IS NULL`.

**Arithmetic over a nullable column.**
`salary + commission_pct` becomes `salary + NVL(commission_pct, 0)`.

**Aggregate in WHERE.**
`WHERE MAX(salary) > 10000` becomes `HAVING MAX(salary) > 10000`.

**Non-aggregated column outside GROUP BY.**
`SELECT department_id, last_name, MAX(salary) ... GROUP BY department_id` becomes either a grouped column list or an aggregate over `last_name`.

**Implicit join.**
`FROM employees, departments` with the condition in `WHERE` becomes `JOIN ... ON ...`.

**Natural join on ambiguous tables.**
`NATURAL JOIN` where two column names are shared becomes an explicit `ON` naming the intended column.

**Multi-row subquery with `=`.**
`WHERE department_id = (SELECT department_id FROM ...)` returning several rows becomes `IN`.

**Date literal relying on the session format.**
`hire_date = '17/02/1996'` becomes `hire_date = TO_DATE('17/02/1996', 'DD/MM/YYYY')`.

**Unnamed constraint.**
`CHECK (salary > 0)` becomes `CONSTRAINT chk_salary_positive CHECK (salary > 0)`.

## Failure modes

- Selecting more columns than the question asked for, or fewer.
- Assuming string comparison is case insensitive; `'king'` does not match `'King'`.
- `BETWEEN` written with the larger bound first, which matches nothing.
- `COUNT(column)` used where `COUNT(*)` was meant, so null rows vanish from the total.
- `AVG` over a nullable column reported as an average over all employees.
- A join that silently drops rows because an inner join was used where an outer join was needed.
- A self join without aliases, which makes every column reference ambiguous.
- `DISTINCT` added to hide duplicate rows produced by a wrong join condition.
- Ordering by a column that is not in the select list when `DISTINCT` is present.
- Comparing a `DATE` against a string and relying on implicit conversion.

## Verification

Before reporting the query as done, confirm all of these:

- The select list matches exactly the columns the question asks for, with readable aliases.
- Filters use the right operators, and nullable columns are tested with `IS NULL`.
- Every non-aggregated select column appears in `GROUP BY`.
- Row filters are in `WHERE`, group filters in `HAVING`.
- Joins have explicit conditions, and the join type matches whether unmatched rows must survive.
- Subqueries return the cardinality the operator expects.
- Date and string literals are converted explicitly where the format is ambiguous.
- The result is sorted when the question implies an order.
- You can state the expected row count or shape for a small example.

## Workflow

1. Restate the question and list the exact output columns.
2. Identify the tables and how they relate before writing anything.
3. Write `FROM` and the joins first, then `WHERE`, then the select list.
4. Add grouping only when the question aggregates, and put the group filter in `HAVING`.
5. Handle nulls explicitly wherever a nullable column is used.
6. Add ordering last.
7. State the expected result shape, and report anything you could not check without running it.
