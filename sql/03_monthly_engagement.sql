SELECT
    month_start,
    COUNT(*) AS enrolled_students,
    SUM(active_flag) AS active_students,
    ROUND(AVG(active_flag), 4) AS active_rate,
    ROUND(AVG(CASE WHEN minutes >= 60 THEN 1.0 ELSE 0.0 END), 4)
        AS dosage_target_rate,
    ROUND(
        AVG(CASE WHEN active_flag = 1 THEN minutes END),
        1
    ) AS avg_minutes_per_active_student
FROM fact_engagement_monthly
GROUP BY month_start
ORDER BY month_start;
