WITH segment_rows AS (
    SELECT
        'Grade level' AS segment_dimension,
        'Grade ' || CAST(ss.grade_level AS TEXT) AS segment,
        ss.baseline_score,
        ss.followup_score,
        ss.score_change
    FROM v_student_summary AS ss

    UNION ALL

    SELECT
        'District locale',
        dd.locale,
        ss.baseline_score,
        ss.followup_score,
        ss.score_change
    FROM v_student_summary AS ss
    JOIN dim_district AS dd
        ON ss.district_id = dd.district_id

    UNION ALL

    SELECT
        'Implementation tier',
        dd.implementation_tier,
        ss.baseline_score,
        ss.followup_score,
        ss.score_change
    FROM v_student_summary AS ss
    JOIN dim_district AS dd
        ON ss.district_id = dd.district_id
)
SELECT
    segment_dimension,
    segment,
    COUNT(*) AS students,
    ROUND(AVG(CASE WHEN followup_score IS NOT NULL THEN 1.0 ELSE 0.0 END), 4)
        AS followup_completion_rate,
    ROUND(AVG(baseline_score), 2) AS avg_baseline_score,
    ROUND(AVG(followup_score), 2) AS avg_followup_score,
    ROUND(AVG(score_change), 2) AS avg_score_change
FROM segment_rows
GROUP BY segment_dimension, segment
ORDER BY segment_dimension, segment;
