-- 017_department_tasks.sql -- a task the Super User gives a department (ENGINE-GAPS #16, decided 2 Oct 2026).
--
-- Such work is rarely a file or a program, so there is no verification stack and no expectations: a title, a
-- deadline, and the Admins who are told. Each Admin marks it seen, ongoing or done; the task stands at the furthest any
-- of them has got; only the Super User who gave it calls it complete, or sends it back with a note every Admin sees.
-- Admin -> Worker tasks (the `tasks` table) keep their checks and are untouched.
-- Mirrored in database-schema.md 4.

CREATE TABLE department_tasks (
    id                    INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    department_id         INTEGER NOT NULL REFERENCES departments(id),
    assigner_account_id   INTEGER NOT NULL REFERENCES accounts(id),
    title                 TEXT NOT NULL,
    deadline_at           TIMESTAMPTZ NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at          TIMESTAMPTZ
);

CREATE INDEX department_tasks_department_idx ON department_tasks (department_id);

-- One row per Admin told. `state_at` is when the state last changed; `seen_at` is the first time it was marked seen
-- (the record of when it was seen, whatever it became after).
CREATE TABLE department_task_admins (
    task_id     INTEGER NOT NULL REFERENCES department_tasks(id),
    account_id  INTEGER NOT NULL REFERENCES accounts(id),
    state       TEXT NOT NULL DEFAULT 'told' CHECK (state IN ('told', 'seen', 'ongoing', 'done')),
    state_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    seen_at     TIMESTAMPTZ,
    PRIMARY KEY (task_id, account_id)
);

-- The notes the Super User sends with a task going back (and, later, anything else said on it): every Admin on it sees them.
CREATE TABLE department_task_notes (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task_id     INTEGER NOT NULL REFERENCES department_tasks(id),
    by_account_id INTEGER NOT NULL REFERENCES accounts(id),
    text        TEXT NOT NULL,
    at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
