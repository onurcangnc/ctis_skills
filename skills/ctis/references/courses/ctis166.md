# CTIS166 — Unix text processing

You are solving a text-transformation task with standard Unix tools composed into a pipeline. The answer is the command, plus what each part of it does, plus at least one alternative built from a different tool. Reaching for a scripting language when a pipeline will do misses the point of the exercise.

Evidence note: the material available for this course is a student's homework answer set rather than instructor handouts. The tool list, the answer format and the man-page-first habit below come from that source and are reliable; grading rules and submission format are not documented and should be asked for rather than assumed.

## Teaching posture

Start at the manual page, not at a remembered flag. The habit being taught is: identify the tool, read its options, choose the one that fits, then compose. Explain the command word by word after giving it, then show a second way to reach the same result with a different tool and say when each is preferable.

Keep every transformation deterministic and reproducible: same input file, same command, same output file, same bytes.

## Scope

`tr`, `sed`, `grep`, `cut`, `sort`, `uniq`, `join`, `comm`, `diff`, `find`, `date`, `cp`, `mv`, pipes, and input and output redirection.

## The answer shape

Every answer follows the same four moves, in this order:

```text
1. Tools consulted:   man tr, man sed
2. What the manual gave:  the option that does the job, named
3. Answer:  cat input.txt | tr '[:upper:]' '[:lower:]' > output.txt
4. Explanation:  cat reads the file and writes it to the pipe;
                 tr replaces every upper-case letter with its lower-case form;
                 > writes the result to output.txt, replacing it.
5. Alternative method:  sed 's/\(.*\)/\L\1/' input.txt > output.txt
```

The alternative is not decoration. Producing the same result with a different tool is how the exercise checks that you understood the transformation rather than memorised a recipe.

## The tools, by job

| Job | Tool | Idiom |
|---|---|---|
| Translate or delete characters | `tr` | `tr '[:upper:]' '[:lower:]'`, `tr -d '\r'`, `tr -s ' '` |
| Substitute by pattern | `sed` | `sed 's/old/new/g'` |
| Select lines | `grep` | `grep -i`, `grep -v`, `grep -c`, `grep -E` |
| Select columns | `cut` | `cut -d: -f1,3` |
| Order lines | `sort` | `sort -n`, `sort -r`, `sort -k2`, `sort -t:` |
| Collapse repeats | `uniq` | `uniq -c`, `uniq -d`, `uniq -u` |
| Merge on a key | `join` | `join -1 1 -2 1 a.txt b.txt` |
| Compare sorted sets | `comm` | `comm -12 a.txt b.txt` |
| Compare files line by line | `diff` | `diff -u old new` |
| Locate files | `find` | `find . -name '*.txt' -mtime -7` |
| Format or compute dates | `date` | `date '+%Y-%m-%d'` |

## Skeletons

### Case conversion

```bash
cat input.txt | tr '[:upper:]' '[:lower:]' > output.txt
tr '[:upper:]' '[:lower:]' < input.txt > output.txt     # no extra process
sed 's/\(.*\)/\L\1/' input.txt > output.txt             # GNU sed
```

Use the character classes rather than `a-z`, so the range is correct for the locale. `tr` works on characters and cannot use patterns; `sed` works on patterns and is the tool when the change depends on context.

### Word frequency

The canonical pipeline, and the one most other exercises are variations of:

```bash
tr -cs '[:alpha:]' '\n' < article.txt \
  | tr '[:upper:]' '[:lower:]' \
  | sort \
  | uniq -c \
  | sort -rn \
  | head -10
```

Read it stage by stage: split into one word per line, normalise the case, sort so equal words are adjacent, count runs, order by count descending, take the top ten. `uniq` only collapses adjacent lines, so the `sort` before it is mandatory, not stylistic.

### Fields

```bash
cut -d: -f1,7 users.txt                      # first and seventh colon-separated fields
sort -t: -k3 -n users.txt                    # numeric sort on the third field
grep -v '^#' config.txt | cut -d= -f2        # drop comments, keep values
```

`cut` needs a single-character delimiter and cannot handle runs of spaces. Squeeze them first with `tr -s ' '` when the columns are space aligned.

### Set operations on two files

```bash
sort a.txt > a.sorted
sort b.txt > b.sorted

comm -12 a.sorted b.sorted      # lines in both
comm -23 a.sorted b.sorted      # only in a
comm -13 a.sorted b.sorted      # only in b
```

`comm` requires both inputs sorted with the same collation, and its three columns are suppressed by number. `join` merges on a key field instead:

```bash
join -t: -1 1 -2 1 users.sorted groups.sorted
```

Both inputs must be sorted on the join field, with the same delimiter.

### Finding files

```bash
find . -type f -name '*.log' -mtime -7
find . -type f -size +1M -exec ls -lh {} \;
find . -type d -empty -delete
```

Put `-name` in quotes so the shell does not expand it before `find` sees it. `-mtime -7` means modified within the last seven days.

### Redirection

```bash
command > out.txt        # replace
command >> out.txt       # append
command 2> err.txt       # standard error only
command > out.txt 2>&1   # both, order matters
command < in.txt         # read from a file
```

`> file` truncates before the command runs, so `sort file > file` empties the file. Write to a new name and rename afterwards.

## Rules with rewrites

**Redirecting into the input file.**
`sort data.txt > data.txt` becomes `sort data.txt > data.sorted && mv data.sorted data.txt`.

**Counting without sorting first.**
`uniq -c words.txt` becomes `sort words.txt | uniq -c`.

**Unnecessary `cat`.**
`cat file | grep pattern` becomes `grep pattern file`.

**Unquoted pattern given to find.**
`find . -name *.txt` becomes `find . -name '*.txt'`.

**Character ranges instead of classes.**
`tr 'A-Z' 'a-z'` becomes `tr '[:upper:]' '[:lower:]'`.

**`cut` on space-aligned columns.**
`cut -d' ' -f2` on padded text becomes `tr -s ' ' | cut -d' ' -f2`.

**Lexicographic sort where numeric was meant.**
`sort -k2` on numbers becomes `sort -k2 -n`.

**`comm` on unsorted input.**
`comm a.txt b.txt` becomes the same after sorting both with the same collation.

**One tool asserted as the only way.**
A single answer becomes the answer plus one alternative built from a different tool.

**Escaping guessed rather than read.**
A remembered flag becomes the option named from the manual page, quoted in the explanation.

## Failure modes

- `uniq` used on unsorted input, which counts each run separately.
- Locale-dependent sorting producing a different order than expected; set `LC_ALL=C` when byte order is required.
- Windows line endings leaving a stray carriage return on every line; strip with `tr -d '\r'`.
- A trailing newline difference making two otherwise identical files compare as different.
- `grep` treating a pattern as a regular expression when a literal was meant; use `grep -F`.
- `sed 's/a/b/'` changing only the first occurrence per line without the `g` flag.
- `find -delete` placed before the filters, so it matches more than intended.
- Whitespace in filenames breaking a pipeline that assumes one word per line.
- `>>` intended but `>` typed, silently discarding earlier output.

## Verification

Before reporting the answer as done, confirm all of these:

- The tools were identified from their manual pages, and the options used are named in the explanation.
- The command is explained word by word, including the redirection.
- At least one alternative using a different tool is given, with a note on when each is preferable.
- Any `uniq`, `comm` or `join` is preceded by the sort it requires.
- No command writes to the file it is reading.
- The pipeline is deterministic: the same input produces the same output bytes.
- The output was checked against a small sample input whose expected result you can state.

## Workflow

1. Restate the transformation: what the input looks like, what the output must look like.
2. Name the tools that could do it and the option from each manual page.
3. Build the pipeline one stage at a time, checking the intermediate output.
4. Redirect to a new file, never to the input.
5. Explain each stage in one sentence.
6. Give an alternative built from a different tool.
7. State the sample input and the expected output, and report anything you could not run.
