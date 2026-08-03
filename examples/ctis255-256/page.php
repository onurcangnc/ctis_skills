<?php
declare(strict_types=1);

function normalizePage(mixed $value, int $pageCount): int
{
    $page = filter_var($value, FILTER_VALIDATE_INT);
    if ($pageCount < 1) {
        return 1;
    }
    if ($page === false) {
        return 1;
    }
    return max(1, min($pageCount, $page));
}

function pageSlice(PDO $database, int $page, int $pageSize): array
{
    $offset = ($page - 1) * $pageSize;
    $statement = $database->prepare(
        'SELECT name, summary FROM catalog_item ORDER BY name, id LIMIT :size OFFSET :offset'
    );
    $statement->bindValue(':size', $pageSize, PDO::PARAM_INT);
    $statement->bindValue(':offset', $offset, PDO::PARAM_INT);
    $statement->execute();
    return $statement->fetchAll(PDO::FETCH_ASSOC);
}

function renderName(string $name): string
{
    return htmlspecialchars($name, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}
