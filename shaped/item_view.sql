-- item_view.sql
CREATE OR REPLACE VIEW item_view AS
SELECT
    c.id AS item_id,
    c.name AS item_name,
    c.body AS item_body,
    c.summary AS item_summary,
    c.start_time AS item_start_time,
    c.end_time AS item_end_time,
    c.audio_bucket_key AS item_audio_bucket_key,
    c.transcript_embedding AS item_transcript_embedding,
    c.created_at AS item_created_at,
    c.updated_at AS item_updated_at,
    fi.id AS feed_item_id,
    fi.name AS feed_item_name,
    fi.body AS feed_item_body,
    fi.audio_url AS feed_item_audio_url,
    fi.audio_bucket_key AS feed_item_audio_bucket_key,
    fi.transcript_bucket_key AS feed_item_transcript_bucket_key,
    fi.duration AS feed_item_duration,
    fi.posted_at AS feed_item_posted_at,
    f.id AS feed_id,
    f.url AS feed_url,
    f.name AS feed_name,
    f.description AS feed_description,
    f.total_itunes_ratings AS feed_total_itunes_ratings,
    f.popularity_percentile AS feed_popularity_percentile,
    f.topic_embedding AS feed_topic_embedding,
    f.artwork_bucket_key AS feed_artwork_bucket_key,
    f.language AS feed_language,
    f.is_english AS feed_is_english,
    string_agg(DISTINCT cat.name, ',' ORDER BY cat.name) AS item_categories,
    string_agg(DISTINCT cat.user_friendly_name, ',' ORDER BY cat.user_friendly_name) AS item_user_friendly_categories,
    json_object_agg(cat.name, ccs.score) FILTER (WHERE cat.name IS NOT NULL) AS item_category_scores
FROM
    web_clip c
JOIN
    web_feeditem fi ON c.feed_item_id = fi.id
JOIN
    web_feed f ON fi.feed_id = f.id
LEFT JOIN
    web_clipcategoryscore ccs ON c.id = ccs.clip_id
LEFT JOIN
    web_category cat ON ccs.category_id = cat.id
GROUP BY
    c.id, fi.id, f.id;