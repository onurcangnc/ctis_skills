# CTIS255 — Frontend Web Technologies

You are building a browser application with HTML, CSS and JavaScript. The tool list is part of the assignment, not a suggestion, and a working application built with the wrong tools loses the points it was meant to earn.

**Ask first whether the class has covered jQuery.** The answer decides the interaction layer:

- **jQuery has been taught.** Every interaction goes through `$`. Raw DOM calls are out: no `document.querySelector`, `getElementById`, `addEventListener`, `innerHTML`, or direct `classList` mutation.
- **jQuery has not been taught yet.** Plain DOM interaction is correct and expected. Do not introduce jQuery.

CSS frameworks are excluded either way. When working inside an existing project that states neither constraint, keep the repository's stack and do not switch it.

## Teaching posture

Define, show the syntax, show the visual result, then set an exercise. Ask a question, let the answer land one step later. Explain why a tool exists before explaining how it works: what problem CSS solves, why a layout method replaced the previous one, what the tree structure buys you. Compare tools side by side with their use cases rather than declaring one best.

Judge the work by behaviour: what happens on click, on Enter, on hover, on refresh. A feature that looks right but does not survive a page refresh is not finished.

## Scope

Semantic HTML, the document tree, CSS selectors and properties, layout with flexbox and grid, jQuery selection, events, effects and DOM manipulation, dialogs and overlays, keyboard interaction, and `localStorage` persistence.

## Hard constraints

These come from the assignment text and override any general web-development instinct:

| Rule | Consequence |
|---|---|
| Use jQuery for UI interactivity, once jQuery has been taught | `document.querySelector`, `getElementById`, `addEventListener`, `innerHTML` and direct `classList` mutation are not acceptable for interactive behaviour |
| Before jQuery has been taught | plain DOM interaction is expected; do not introduce jQuery early |
| jQuery plugins allowed | a datepicker or sortable plugin is fine |
| CSS frameworks not allowed | no Bootstrap, no Materialize, no Tailwind |
| Icon and font libraries allowed | Font Awesome or similar is fine |
| Match the given layout | the visual result is compared against the supplied figure |
| Team of 3 or 4, one uploader | one submission per group, through the course system |
| Filename fixed | `Name_Surname.zip`, exactly the pattern given |
| Late submission penalised | a fixed negative item on the rubric |

The grading sheet is behavioural, item by item, with points attached to each interaction and negative items for CSS fidelity and lateness. Read it as a checklist and satisfy the items one at a time.

## The required shape

Three files, separated by concern. Never inline a style attribute or an event handler in the markup.

```text
index.html      structure only, semantic elements, no style or onclick attributes
style.css       all presentation
app.js          all behaviour, wrapped in the ready handler
```

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>To-Do</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <aside id="sidePanel">
        <button id="newListButton">+ New List</button>
        <ul id="taskList"></ul>
    </aside>

    <main id="taskPage"></main>

    <div id="overlay" class="hidden">
        <div id="dialog">
            <h2>New Task Name</h2>
            <input type="text" id="taskNameInput">
            <button id="createButton">Create</button>
            <button id="cancelButton">Cancel</button>
        </div>
    </div>

    <script src="jquery.min.js"></script>
    <script src="app.js"></script>
</body>
</html>
```

Indentation is required, not cosmetic: the markup is read as a tree, and the indentation is what makes the parent, child and sibling relations visible.

## Skeletons

### Ready handler and delegated events

Content created after page load will not respond to a direct binding. Delegate from a container that exists at load time.

```javascript
$(function () {
    // direct binding: the element exists in the markup
    $("#newListButton").on("click", openDialog);

    // delegated binding: .taskItem elements are created later
    $("#taskPage").on("click", ".taskItem", function () {
        toggleItem($(this).data("id"));
    });

    render();
});
```

`$(this)` inside a handler is the jQuery object for the element that fired the event. `this` alone is the raw element and has no jQuery methods.

### Dialog with overlay and focus

```javascript
function openDialog() {
    $("#overlay").removeClass("hidden");
    $("#taskNameInput").val("").trigger("focus");   // focus at the beginning
}

$("#cancelButton").on("click", function () {
    $("#overlay").addClass("hidden");
});

$("#createButton").on("click", createTask);

$("#taskNameInput").on("keyup", function (event) {
    if (event.key === "Enter") {
        createTask();
    }
});
```

Two ways to confirm, one code path: the button and the Enter key both call `createTask`. Wire them separately and let them share the function.

```css
#overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);   /* semi-transparent grey */
    display: flex;
    align-items: center;
    justify-content: center;
}

#overlay.hidden { display: none; }
```

### Validate before accepting

```javascript
function createTask() {
    const name = $("#taskNameInput").val().trim();

    if (name === "") {
        $("#taskNameInput").addClass("invalid").trigger("focus");
        return;                      // an empty name is rejected
    }

    tasks.push({ id: Date.now(), name: name, items: [] });
    save();
    render();
    $("#overlay").addClass("hidden");
}
```

Trim before testing for empty, so a name of spaces is rejected too.

### Building elements with jQuery

```javascript
function renderTasks() {
    const list = $("#taskList").empty();

    tasks.forEach(function (task) {
        const remaining = task.items.filter(item => !item.done).length;

        const row = $("<li>")
            .addClass("taskRow")
            .attr("data-id", task.id)
            .append($("<span>").addClass("taskName").text(task.name))
            .append($("<span>").addClass("badge").text(remaining > 0 ? remaining : ""))
            .append($("<i>").addClass("fa fa-trash trashIcon"));

        list.append(row);
    });
}
```

Use `.text()` for anything typed by the user. `.html()` with user input injects whatever they typed as markup. The badge is empty rather than zero when nothing is outstanding, which is what the rubric asks for.

### Toggle and cross off

```javascript
function toggleItem(taskId, itemId) {
    const task = tasks.find(t => t.id === taskId);
    const item = task.items.find(i => i.id === itemId);

    item.done = !item.done;
    save();
    render();
}
```

```css
.taskItem.done .itemTitle {
    text-decoration: line-through;
    color: #888;
}
```

The state lives in the data, the appearance lives in a CSS class, and rendering derives one from the other. Never read the current state back out of the markup.

### Hover-revealed control

```css
.trashIcon { visibility: hidden; }
.taskRow:hover .trashIcon { visibility: visible; }
```

Use `visibility` or `opacity` rather than `display: none`, so the row does not change width when the icon appears.

### Persistence with localStorage

```javascript
const STORAGE_KEY = "tasks.v1";

function save() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
}

function load() {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
}

let tasks = load();
```

`localStorage` stores strings only, so every write is `JSON.stringify` and every read is `JSON.parse`. Save after every change, and prove it by refreshing the page.

### Layout

```css
body {
    display: flex;
    min-height: 100vh;
    margin: 0;
}

#sidePanel { flex: 0 0 280px; }
#taskPage  { flex: 1; }
```

Flexbox for a single axis, grid for two. `float` is left over from older layouts and is not the tool for this. When the assignment supplies a figure, match its proportions, spacing and colours; those points are awarded on fidelity.

## Rules with rewrites

**DOM API used for interactivity after jQuery was taught.**
`document.getElementById("newListButton").addEventListener("click", open)` becomes `$("#newListButton").on("click", open)`. Before jQuery is taught the first form is the correct answer, so confirm which applies before rewriting.

**Direct binding to generated content.**
`$(".taskItem").on("click", handler)` for elements created later becomes `$("#taskPage").on("click", ".taskItem", handler)`.

**CSS framework pulled in.**
A Bootstrap link tag becomes your own `style.css` with the layout written by hand.

**Inline handler in the markup.**
`<button onclick="createTask()">` becomes a plain button plus a binding in `app.js`.

**Inline style in the markup.**
`<div style="color:red">` becomes a class in `style.css`.

**User input inserted as markup.**
`.html(task.name)` becomes `.text(task.name)`.

**State read from the DOM.**
`if ($(row).hasClass("done"))` becomes `if (item.done)`, with the class rendered from the data.

**Empty input accepted.**
`if (name)` becomes `if (name.trim() === "") { ... return; }`.

**Enter key ignored.**
A dialog with only a Create button becomes one that also handles `keyup` with `event.key === "Enter"`.

**State kept only in memory.**
A change that updates the array becomes one that updates the array and calls `save()`.

**Zero shown where the rubric asks for nothing.**
`.text(remaining)` becomes `.text(remaining > 0 ? remaining : "")`.

**Raw element treated as a jQuery object.**
`this.addClass("done")` becomes `$(this).addClass("done")`.

## Failure modes

- Binding events outside the ready handler, so the elements do not exist yet.
- Re-rendering the whole list and losing the focus that the rubric requires to be in a textbox.
- Forgetting `JSON.parse` on read, so `tasks` becomes a string and `forEach` fails.
- Storing an object with a circular reference, which makes `JSON.stringify` throw.
- Using `keypress` for the Enter key, which is deprecated and skips some keys; use `keyup`.
- Deleting a task without deleting its items, leaving orphans in storage.
- Comparing a numeric id with a string id read from a `data-` attribute.
- An overlay that intercepts clicks after it is hidden, because only its opacity changed.
- Layout that collapses at a narrower window because a fixed pixel width was used where a flexible one was needed.

## Verification

Work through the rubric item by item. Before reporting the work as done, confirm all of these:

- The interaction layer matches what the class has covered: once jQuery has been taught, every interaction routes through `$` with no raw `document.querySelector`, `getElementById`, `addEventListener`, `innerHTML` or `classList` call; before that, plain DOM calls are correct.
- No CSS framework is linked, in either case.
- Structure, presentation and behaviour live in three separate files.
- Every generated element is reached through a delegated binding.
- The dialog opens with the textbox focused, closes on Cancel, and confirms on both Create and Enter.
- Empty and whitespace-only input is rejected.
- The counter shows a number only when something is outstanding.
- Hovering reveals the delete control, and deleting removes the task and its items.
- Every change is written to `localStorage`, and a page refresh restores the exact state.
- The rendered layout matches the supplied figure.
- The submitted archive follows the required filename pattern.

## Workflow

1. Confirm whether the class has covered jQuery, and say which interaction layer you are using because of that answer.
2. Read the rubric and turn each numbered item into a checklist entry with its points.
3. Write the markup as a semantic tree, with ids for the fixed containers.
4. Write the CSS for the layout first, then the visual detail, matching the given figure.
5. Define the data model and the `save` and `load` pair before writing any handler.
6. Implement one rubric item at a time, and check it in the browser before moving on.
7. Bind events in the ready handler, delegating anything generated.
8. Refresh the page and confirm the state survives.
9. Report which rubric items you verified and which you could not.
