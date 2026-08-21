SELECT
    g.id,
    g.created_by,
    count(DISTINCT t.id) AS thread_count,
    count(m.id) AS message_count
FROM groups g
LEFT JOIN threads t ON t.group_id = g.id
LEFT JOIN messages m ON m.thread_id = t.id
WHERE g.settings->>'kind' = 'personal'
GROUP BY g.id, g.created_by
ORDER BY g.created_by;
