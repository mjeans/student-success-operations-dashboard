SELECT
    'Duplicate student identifiers' AS quality_rule,
    COUNT(*) AS failing_records,
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END AS status
FROM (
    SELECT student_id
    FROM dim_student
    GROUP BY student_id
    HAVING COUNT(*) > 1
)

UNION ALL

SELECT
    'Duplicate student-month records',
    COUNT(*),
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END
FROM (
    SELECT student_id, month_start
    FROM fact_engagement_monthly
    GROUP BY student_id, month_start
    HAVING COUNT(*) > 1
)

UNION ALL

SELECT
    'Engagement rows without a student',
    COUNT(*),
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END
FROM fact_engagement_monthly AS fe
LEFT JOIN dim_student AS st
    ON fe.student_id = st.student_id
WHERE st.student_id IS NULL

UNION ALL

SELECT
    'Invalid engagement values',
    COUNT(*),
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END
FROM fact_engagement_monthly
WHERE minutes < 0
    OR sessions < 0
    OR lessons_completed < 0
    OR active_flag NOT IN (0, 1)

UNION ALL

SELECT
    'Invalid assessment scores',
    COUNT(*),
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END
FROM fact_assessment
WHERE score < 0 OR score > 100

UNION ALL

SELECT
    'Support tickets without a school',
    COUNT(*),
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END
FROM fact_support_ticket AS ft
LEFT JOIN dim_school AS sc
    ON ft.school_id = sc.school_id
WHERE sc.school_id IS NULL

UNION ALL

SELECT
    'Schools missing implementation status',
    COUNT(*),
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END
FROM dim_school AS sc
LEFT JOIN fact_implementation AS fi
    ON sc.school_id = fi.school_id
WHERE fi.school_id IS NULL;
