DROP VIEW IF EXISTS events_view;

CREATE VIEW events_view AS
SELECT
    cuv.user_id AS user_id,
    cuv.clip_id AS item_id,
    cuv.created_at AS created_at,
    cuv.updated_at AS updated_at,
    'view' AS event_type,
    cuv.duration AS duration
FROM
    web_clipuserview cuv;