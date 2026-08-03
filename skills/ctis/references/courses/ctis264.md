# CTIS264 — Python algorithms

You are writing algorithm code for a course that grades the algorithm, not the answer. A one-line library call that produces the right output scores zero when the assignment names an algorithm. Write the named algorithm, in the course's shape, and prove it ran correctly.

## Teaching posture

Algorithm first, library second. Translate the pseudocode literally before making it idiomatic. State the invariant a loop or recursive call maintains. Show a correctness witness before reporting a timing number. When a student asks for a shortcut that skips the assigned algorithm, give the algorithm and explain why the shortcut fails the assessment.

## Scope

Sorting, searching, string matching, recursion, graphs, trees, heaps, matrices, tabular data with pandas, timing experiments, and matplotlib plots. Route here when the task names an algorithm, a traversal, a complexity class, or Python data work.

The named algorithms of this course: merge sort, quick sort with the Lomuto partition, DFS, BFS, topological sort, brute-force string matching, the GCD approaches, polynomial evaluation, and bottom-up heap construction. Every one of them is assessed under the name and signature the lab guide uses, so the name is part of the answer.

## The required shape

Every algorithm function carries a three-line contract comment, copied from the pseudocode into the body. This is not decoration. It is how the course states what the function accepts and returns.

```python
def SelectionSort(A):
    # Sorts a given array by selection sort
    # Input: An array A[0..n-1] of orderable elements
    # Output: Array A[0..n-1] sorted in ascending order
    for i in range(len(A) - 1):
        smallest = i
        for j in range(i + 1, len(A)):
            if A[j] < A[smallest]:
                smallest = j
        A[i], A[smallest] = A[smallest], A[i]
    return A
```

Three rules from that block:

1. **Name the function exactly as the algorithm is named.** `SelectionSort`, `MergeSort`, `BruteForceStringMatch`, `ComparisonCounting`, `HeapBottomUp`, `BubbleSort`. PascalCase, no abbreviation, no `sort_list` or `my_sort`. When the assignment dictates method names, use those characters exactly, even when they mix conventions: `Insert_node`, `get_left_child`, `set_root_val`, `preorderTrav`. The lab guides themselves mix conventions, and the guide name wins every time: `quickSort` and `partition` are camelCase, `dfs_recursive` and `bfs` are snake_case, `topologicalSort` is camelCase, while `MergeSort` is PascalCase.
2. **Write the purpose, Input, and Output lines** in that order, describing the array as `A[0..n-1]`.
3. **Put the driver at module level under a `#main` comment**, not inside `if __name__ == "__main__"`. These files are run directly.

## Skeletons

### Array algorithm with a witness

```python
def BubbleSort(A):
    # Sorts a given array by bubble sort
    # Input: An array A[0..n-1] of orderable elements
    # Output: Array A[0..n-1] sorted in ascending order
    for i in range(len(A) - 1):
        for j in range(len(A) - 1 - i):
            if A[j + 1] < A[j]:
                A[j], A[j + 1] = A[j + 1], A[j]
    return A

#main
sample = [29, 10, 14, 37, 13]
assert BubbleSort(list(sample)) == sorted(sample)
assert BubbleSort([]) == []
assert BubbleSort([7]) == [7]
print("Sorted:", BubbleSort(list(sample)))
```

The three asserts are the correctness witness: a normal case, an empty case, and a single-element case. Print output alone is not a witness.

### Brute-force string match

```python
def BruteForceStringMatch(T, P):
    # Implements brute-force string matching
    # Input: Strings T (text) and P (pattern)
    # Output: Index of the first matching substring, or -1
    for i in range(len(T) - len(P) + 1):
        j = 0
        while j < len(P) and P[j] == T[i + j]:
            j += 1
        if j == len(P):
            return i
    return -1
```

The `+ 1` matters. `range(len(T) - len(P))` never tests the last valid start position, so a pattern sitting at the end of the text wrongly returns -1. Cover it:

```python
assert BruteForceStringMatch("algorithm", "thm") == 6
assert BruteForceStringMatch("algorithm", "zzz") == -1
```

### Quick sort with Lomuto partition

The lab guide names the two functions `quickSort(A, l, r)` and `partition(A, l, r)`, pivot `A[l]`, scan from `l + 1`. Copy those names and that signature exactly.

```python
def partition(A, l, r):
    # Partitions a subarray by the Lomuto method
    # Input: Subarray A[l..r] of orderable elements
    # Output: Index s of the pivot's final position
    p = A[l]
    s = l
    for i in range(l + 1, r + 1):
        if A[i] < p:
            s += 1
            A[s], A[i] = A[i], A[s]
    A[l], A[s] = A[s], A[l]
    return s


def quickSort(A, l, r):
    # Sorts a subarray by quick sort
    # Input: Subarray A[l..r] of orderable elements
    # Output: None; the subarray is sorted in place
    if l < r:
        s = partition(A, l, r)
        quickSort(A, l, s - 1)
        quickSort(A, s + 1, r)

#main
sample = [29, 10, 14, 37, 13]
expected = sorted(sample)
quickSort(sample, 0, len(sample) - 1)
assert sample == expected
print("Sorted:", sample)
```

`quickSort(A, l, r)` needs three arguments: it cannot be called as `quickSort(A)`. The expected result is captured before the call, because the sort runs in place. Take the expected value first, then sort, then assert.

### Bottom-up heap, index 0 reserved

The heap representation stores the root at index 1 and leaves index 0 unused. Say so in the output, because a reader who assumes zero-indexing misreads every level.

```python
def HeapBottomUp(H):
    # Constructs a heap from an array by the bottom-up algorithm
    # Input: An array H[1..n] of orderable elements, H[0] unused
    # Output: A heap H[1..n]
    n = len(H) - 1
    for i in range(n // 2, 0, -1):
        k = i
        v = H[k]
        heap = False
        while not heap and 2 * k <= n:
            j = 2 * k
            if j < n and H[j] < H[j + 1]:
                j += 1
            if v >= H[j]:
                heap = True
            else:
                H[k] = H[j]
                k = j
        H[k] = v
    return H

#main
H = [0, 2, 9, 7, 6, 5, 8, 10]   # index 0 is a reserved slot, not data
print("Ignore index 0 in every array below")
print("Heap:", HeapBottomUp(H))
print("Root:", H[1])
```

Keep the reserved slot when the algorithm is defined on `H[1..n]`. Do not silently switch to zero-indexing and shift every child formula.

### Graph as a dictionary, recursive DFS

The graph is built from a vertex list and an adjacency matrix, then stored as `{vertex: [neighbours]}`. Build that dictionary explicitly rather than traversing the matrix directly. The lab guide calls the traversal `dfs_recursive(graph, vertex, path)`; the caller passes an empty list as `path`.

```python
def BuildGraph(vertices, matrix):
    # Builds an adjacency-list graph from an adjacency matrix
    # Input: Vertex list V[0..n-1] and matrix M[0..n-1][0..n-1]
    # Output: Dictionary {vertex: list of neighbour vertices}
    return {
        vertices[i]: [vertices[j] for j in range(len(vertices)) if matrix[i][j]]
        for i in range(len(vertices))
    }


def dfs_recursive(graph, vertex, path):
    # Implements a depth-first-search traversal of a given graph
    # Input: Graph {vertex: neighbours}, a start vertex, and an empty path list
    # Output: path holding vertices in visit order
    path.append(vertex)
    for neighbour in graph[vertex]:
        if neighbour not in path:
            dfs_recursive(graph, neighbour, path)
    return path

#main
g = {"a": ["b", "c"], "b": ["a"], "c": ["a"]}
assert dfs_recursive(g, "a", []) == ["a", "b", "c"]
```

Mark the vertex visited on entry, before the loop. Marking it after the recursive call revisits nodes and never terminates on a cycle. The `path` list doubles as the visited record, so a fresh list is passed on every call; see the mutable-default rule below for what happens when that is skipped.

### BFS with a queue

The lab guide calls the traversal `bfs(graph, vertex)` and returns the visit order.

```python
from collections import deque


def bfs(graph, vertex):
    # Implements a breadth-first-search traversal of a given graph
    # Input: Graph {vertex: neighbours} and a start vertex
    # Output: List of vertices in visit order
    visited = []
    queue = deque([vertex])
    while queue:
        current = queue.popleft()
        if current not in visited:
            visited.append(current)
            queue.extend(graph[current])
    return visited

#main
g = {"a": ["b", "c"], "b": ["a"], "c": ["a"]}
assert bfs(g, "a") == ["a", "b", "c"]
```

A vertex is visited once and its unvisited neighbours enter the queue. The `visited` list records discovery, the queue holds the frontier, and each vertex reaches the list exactly once.

### OOP binary tree

When the assignment lists method names, implement that exact list with nothing renamed.

```python
class BinaryTree:
    def __init__(self, root_value):
        self.key = root_value
        self.left = None
        self.right = None

    def Insert_node(self, new_node_value):
        # Inserts a value into the sorted binary tree, recursively
        # Input: A comparable value
        # Output: None; the tree now contains the value
        if new_node_value < self.key:
            if self.left is None:
                self.left = BinaryTree(new_node_value)
            else:
                self.left.Insert_node(new_node_value)
        else:
            if self.right is None:
                self.right = BinaryTree(new_node_value)
            else:
                self.right.Insert_node(new_node_value)

    def get_left_child(self):
        return self.left

    def get_right_child(self):
        return self.right

    def set_root_val(self, value):
        self.key = value

    def get_root_val(self):
        return self.key

    def inorderTrav(self, out):
        if self.left:
            self.left.inorderTrav(out)
        out.append(self.key)
        if self.right:
            self.right.inorderTrav(out)
        return out
```

In-order traversal of a sorted binary tree returns sorted values. That is the free correctness check: `assert tree.inorderTrav([]) == sorted(numbers)`.

### Timing experiment

```python
import time

start = time.time()
result = SelectionSort(data)
end = time.time()

print("Sorted first 10:", result[:10])
print("Seconds:", end - start)
```

Time only the algorithm. Data generation, file reading, and printing sit outside the measured region. Always print a result witness beside the elapsed time, or the number proves nothing.

### Tabular data and plots

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

scores = pd.read_csv("scores.csv")
print(scores)                                   # inspect after reading

scores["adjusted"] = scores["grades"] * 1.23
print(scores)                                   # inspect after deriving

merged = pd.merge(left=area, right=population, left_on="Country", right_on="Country")
merged = merged.fillna(0)
merged["Density"] = merged["Population"] / merged["Area(sqm)"]
merged = merged.replace(np.inf, np.nan).dropna()
print(merged)                                   # inspect after cleaning

plt.hist(scores["grades"], bins=5, histtype="step")
plt.xlabel("Grade")
plt.ylabel("Students")
plt.title("Grade distribution, 5 bins")
plt.show()
```

Print the frame after each stage: read, derive, merge, clean. A single print at the end hides which step broke the data. Division that can produce infinity gets `replace(np.inf, np.nan)` before any aggregation.

Every plot ends with an x label, a y label, and a title. An unlabelled plot is incomplete work.

## Rules with rewrites

**Replacing the assigned algorithm.**
`return sorted(A)` becomes the full `SelectionSort` body. The library call is correct and worthless here.

**Renaming the algorithm.**
`def sort_the_list(items)` becomes `def SelectionSort(A)`.

**Dropping the contract comment.**
`def MergeSort(A):` followed straight by code becomes the same line followed by the purpose, Input, and Output lines.

**Shadowing a builtin.**
`min = i` inside a loop becomes `smallest = i`. `def min(a, b)` becomes `def Minimum(a, b)`. Both shadow builtins the rest of the file still needs.

**Aliasing numpy unusually.**
`import numpy as n` becomes `import numpy as np`. Keep the name `n` for the array length, where the pseudocode uses it.

**Silent recursion.**
A recursive function with no base case, or whose recursive call does not shrink the input, becomes one whose first statement handles the smallest case and whose call passes a strictly smaller argument.

**Mutable default accumulator.**
`def inorderTrav(self, out=[])` becomes `def inorderTrav(self, out)` with the caller passing `[]`. The default list is created once and leaks values between calls. The same defect appears verbatim in the lab guide for Lab 7 Q1 as `def dfs_recursive(graph, vertex, path=[])`: run twice, the second call starts from the first call's leftover path instead of an empty one: `['a', 'b']`, then `['a', 'b', 'a']`, then `['a', 'b', 'a', 'a']` on consecutive runs. The default is created once at definition time, not per call. Fix by removing the default and passing a fresh `[]` at each call site, and inside the body use `path.append(vertex)`. The guide's `path += vertex` string trick only works for single-character vertex names, and breaks on multi-character ones.

**Timing the wrong region.**
`start` before data generation becomes `start` immediately before the algorithm call.

**Reference result taken after an in-place sort.**
`SelectionSort(data)` followed by `assert data == sorted(data)` becomes `expected = sorted(data)` computed first, then the sort, then `assert result == expected`. Sorting in place makes the late comparison compare the list with itself, so a broken sort still passes.

**Unlabelled plot.**
`plt.plot(x, y); plt.show()` becomes the same plot with `xlabel`, `ylabel`, and `title` before `show`.

## Failure modes

- Off-by-one in a scan range, most often the missing `+ 1` in brute-force string matching.
- Marking a graph vertex visited after the recursive call instead of on entry.
- Mixing one-indexed heap formulas with a zero-indexed array, so children resolve to the wrong slots.
- Computing metrics before cleaning missing values, or merging on a key that exists under two different names.
- Comparing floats with `==` instead of a tolerance.
- Capturing the expected result after an in-place algorithm has already run, so the assertion is vacuous.
- Calling `quickSort(A)` with one argument when the lab guide requires three, `quickSort(A, l, r)`, so the call fails before any sorting happens.
- Assigning the result of `MergeSort(A)`: it returns nothing and sorts in place, so `A = MergeSort(A)` leaves `A` holding `None`.
- Returning `None` from a function whose Output line promises an array, because the `return` sits inside the loop.
- Reading a file inside the algorithm function, which makes the algorithm untestable without that file.

## Verification

Before reporting the work as done, confirm all of these:

- The named algorithm exists as a function with that exact name and its three-line contract.
- At least one `assert` covers a normal case and one covers an edge case: empty, single element, not found, or duplicate.
- Recursion has a base case and provably shrinks its input.
- File and input parsing happen outside the algorithm function.
- Timing measures only the algorithm, and a result witness prints beside the elapsed time.
- Every plot has an x label, a y label, and a title.
- Data work prints the frame after read, derive, merge, and clean.

## Workflow

1. Restate the input and output contract and name the algorithm the task requires.
2. Write the function signature and its three-line contract comment before any logic.
3. Implement the algorithm literally from the pseudocode, keeping the pseudocode's index base.
4. Add the `#main` driver with asserts for a normal case and an edge case.
5. Run it mentally on a small hand-checkable input and state the expected output.
6. Add timing or plotting only after correctness is proven.
7. Report what was verified and what was not.
