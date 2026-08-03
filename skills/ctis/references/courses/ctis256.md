# CTIS256 — Database-Backed Web Programming

You are writing server-side PHP that talks to MySQL through PDO and renders HTML. The assignments are behavioural and point-weighted: listing, paging, cart, and each edge of the navigation is worth its own points. Build them one at a time and check each in the browser.

## Teaching posture

Same rhythm as the frontend course: definition, syntax, visual result, exercise. Give the SQL idiom the task needs and let the student assemble the application around it. Prefer a small runnable page over an explanation. When something can be done two ways, name the trade-off rather than declaring a winner.

Never let a query be built by pasting a variable into a string. Parameter binding is taught as the default, not as a security lecture appended at the end.

## Scope

PDO connection and error modes, prepared statements, SELECT with `LIMIT` for paging, counting rows for page numbers, sessions for cart state, form handling with GET and POST, output escaping, and rendering result sets into HTML templates.

## The required shape

Separate the connection, the queries and the presentation.

```text
config.php      the account the assignment supplies
db.php          the PDO connection, included everywhere
products.php    listing with paging
cart.php        cart operations and display
style.css
```

```php
<?php
// config.php - the account the assignment supplies, kept in one place
define("DB_DSN",  "mysql:host=localhost;dbname=test;charset=utf8mb4");
define("DB_USER", "std");
define("DB_PASS", "");
```

```php
<?php
// db.php - one connection, reused by every page
require_once "config.php";

try {
    $db = new PDO(DB_DSN, DB_USER, DB_PASS);
    $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $db->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
} catch (PDOException $e) {
    die("Database connection failed.");   // message to the user, detail to the log
}
```

The assignment states the account it wants you to use, including whether the password is an empty string with nothing between the quotes. Put those values in `config.php` and nothing else, so the rest of the code can be read, copied and submitted without the account travelling with it.

Two attributes, always: exceptions rather than silent failure, and associative fetch so `$row["name"]` works. Include `db.php` from every page; never open a second connection.

## Skeletons

### Prepared statement, always

```php
$statement = $db->prepare("SELECT * FROM products WHERE id = :id");
$statement->execute([":id" => $id]);
$product = $statement->fetch();
```

The value never enters the SQL text. This is the single rule that the rest of the course builds on.

`LIMIT` is the exception that catches people out: MySQL will not accept a bound parameter for the offset and row count in every driver configuration. Cast to integer and interpolate those two only, after validating them:

```php
$perPage = 3;
$page    = isset($_GET["page"]) ? (int)$_GET["page"] : 1;
if ($page < 1) {
    $page = 1;
}
$offset = ($page - 1) * $perPage;

$statement = $db->prepare("SELECT * FROM products ORDER BY id LIMIT $offset, $perPage");
$statement->execute();
$products = $statement->fetchAll();
```

The cast to `int` is what makes the interpolation safe. Everything that is not an offset or a row count stays bound.

### Paging

`LIMIT offset, count`: the first number is the index of the first record, the second is how many to fetch. `LIMIT 0,3` gives the first three, `LIMIT 3,3` the next three.

```php
// total pages
$total     = (int)$db->query("SELECT COUNT(*) FROM products")->fetchColumn();
$pageCount = (int)ceil($total / $perPage);

if ($page > $pageCount) {
    $page = $pageCount;
}
```

```php
<nav class="paging">
    <?php if ($page > 1): ?>
        <a href="?page=<?= $page - 1 ?>"><img src="icons/prev.png" alt="Previous"></a>
    <?php else: ?>
        <img src="icons/prev.png" alt="Previous" class="disabled">
    <?php endif; ?>

    <?php for ($p = 1; $p <= $pageCount; $p++): ?>
        <a href="?page=<?= $p ?>" class="<?= $p === $page ? 'current' : '' ?>"><?= $p ?></a>
    <?php endfor; ?>

    <?php if ($page < $pageCount): ?>
        <a href="?page=<?= $page + 1 ?>"><img src="icons/next.png" alt="Next"></a>
    <?php else: ?>
        <img src="icons/next.png" alt="Next" class="disabled">
    <?php endif; ?>
</nav>
```

The two edges are graded: on the first page the previous control must not work, on the last page the next control must not work. Render them as a non-link, not as a link that silently does nothing.

### Rendering rows with escaping

```php
<?php foreach ($products as $product): ?>
    <div class="product">
        <img src="images/<?= htmlspecialchars($product["image"]) ?>"
             alt="<?= htmlspecialchars($product["name"]) ?>">
        <h3><?= htmlspecialchars($product["name"]) ?></h3>
        <p class="price"><?= number_format($product["price"], 2) ?> TL</p>
        <form method="post" action="cart.php">
            <input type="hidden" name="id" value="<?= (int)$product["id"] ?>">
            <button type="submit" name="action" value="add">Add to cart</button>
        </form>
    </div>
<?php endforeach; ?>
```

Every value taken from the database and printed into HTML goes through `htmlspecialchars`. Use the alternate syntax (`foreach: ... endforeach;`) inside templates; it keeps the markup readable.

### Cart in the session

```php
<?php
session_start();                       // before any output

if (!isset($_SESSION["cart"])) {
    $_SESSION["cart"] = [];            // productId => quantity
}

if ($_SERVER["REQUEST_METHOD"] === "POST") {
    $id     = (int)$_POST["id"];
    $action = $_POST["action"] ?? "";

    if ($action === "add") {
        $_SESSION["cart"][$id] = ($_SESSION["cart"][$id] ?? 0) + 1;
    } elseif ($action === "remove") {
        unset($_SESSION["cart"][$id]);
    }

    header("Location: cart.php");      // redirect after post
    exit;
}
```

`session_start()` runs before anything is printed, including a stray blank line before `<?php`. Redirect after a successful POST so a refresh does not repeat the action.

### Reading the cart back

```php
$ids = array_keys($_SESSION["cart"]);

if ($ids) {
    $placeholders = implode(",", array_fill(0, count($ids), "?"));
    $statement = $db->prepare("SELECT * FROM products WHERE id IN ($placeholders)");
    $statement->execute($ids);
    $rows = $statement->fetchAll();
}
```

An `IN` list needs one bound marker per value. Building that marker string from the count keeps the statement prepared.

## Rules with rewrites

**Value pasted into SQL.**
`"SELECT * FROM products WHERE id = $id"` becomes a prepared statement with `:id` bound.

**Unvalidated paging input.**
`$page = $_GET["page"];` becomes `$page = isset($_GET["page"]) ? (int)$_GET["page"] : 1;` with a lower bound.

**Database value printed raw.**
`<?= $product["name"] ?>` becomes `<?= htmlspecialchars($product["name"]) ?>`.

**Silent database errors.**
A connection without `ATTR_ERRMODE` becomes one that sets `ERRMODE_EXCEPTION` and wraps the construction in try/catch.

**Connection repeated per page.**
A `new PDO(...)` in each file becomes one `db.php` that every page includes.

**Disabled control rendered as a link.**
`<a href="?page=0">` on the first page becomes a non-link element with a disabled class.

**Page count computed from the fetched rows.**
`count($products)` becomes a separate `SELECT COUNT(*)` divided by the page size and rounded up.

**Cart stored in a global.**
A module-level array becomes `$_SESSION["cart"]`, with `session_start()` at the top.

**POST handled without a redirect.**
Rendering the page directly after a POST becomes `header("Location: ...")` followed by `exit`.

**Exception detail shown to the user.**
`die($e->getMessage())` becomes a generic message for the user and the detail written to the log.

## Failure modes

- Output before `session_start()` or before `header()`, which triggers a headers-already-sent error. A blank line before `<?php` counts as output.
- `fetch()` used where `fetchAll()` was needed, so only the first row appears.
- `LIMIT` values bound as strings, which MySQL rejects; cast to `int` and interpolate only those.
- Offset computed as `$page * $perPage`, which skips the first page.
- `ceil` applied to an integer division that already truncated.
- Comparing an id from `$_GET` with a database id without casting, so a loose comparison passes wrongly.
- A cart keyed by array position rather than product id, which breaks when an item is removed.
- Missing `charset=utf8mb4` in the DSN, which mangles non-ASCII product names.
- Forgetting that `unset` on an array element leaves the remaining keys unchanged; do not assume they are renumbered.

## Verification

Before reporting the work as done, confirm all of these:

- Every query that takes a value uses a prepared statement; only validated integer `LIMIT` parts are interpolated.
- The connection sets exception mode and associative fetch, and lives in one shared file.
- Every database value printed into HTML is escaped.
- Paging shows the correct page count, and both edge controls are inert at the first and last pages.
- The current page is visually marked.
- The cart survives navigation, and a refresh after adding does not add twice.
- `session_start()` runs before any output.
- Each numbered item in the assignment has been checked in the browser.

## Workflow

1. Turn the assignment's numbered items into a checklist with their points.
2. Import the supplied SQL and inspect the table columns before writing any query.
3. Write `db.php` and confirm the connection with one trivial query.
4. Build the listing with a fixed page size, then add paging, then the edge cases.
5. Add the cart with sessions, then the redirect after post.
6. Escape every output and re-check the pages in the browser.
7. Report which numbered items you verified and which you could not.
