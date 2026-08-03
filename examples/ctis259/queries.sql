SELECT t.name, COUNT(w.id) AS item_count, COALESCE(SUM(w.points), 0) AS total_points
FROM team AS t
LEFT JOIN work_item AS w ON w.team_id = t.id
GROUP BY t.id, t.name
ORDER BY total_points DESC, t.name ASC;

SELECT DISTINCT t.name
FROM team AS t
JOIN work_item AS w ON w.team_id = t.id
WHERE w.state = :state AND w.points >= :minimum
ORDER BY t.name;
