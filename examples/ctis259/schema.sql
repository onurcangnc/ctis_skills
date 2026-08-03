CREATE TABLE team (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE work_item (
    id INTEGER PRIMARY KEY,
    team_id INTEGER REFERENCES team(id),
    points INTEGER NOT NULL CHECK (points >= 0),
    state TEXT NOT NULL CHECK (state IN ('open', 'done'))
);

INSERT INTO team(id, name) VALUES
    (1, 'Amber'),
    (2, 'Blue'),
    (3, 'Copper');

INSERT INTO work_item(id, team_id, points, state) VALUES
    (1, 1, 0, 'open'),
    (2, 1, 5, 'done'),
    (3, 1, 5, 'done'),
    (4, 2, 8, 'done'),
    (5, NULL, 3, 'open');
