WITH ticket_kpis AS (
    SELECT
        AVG(CASE WHEN response_hours <= 24 THEN 1.0 ELSE 0.0 END)
            AS support_sla_rate
    FROM fact_support_ticket
),
school_risk AS (
    SELECT
        school_id,
        (
            CASE WHEN activation_rate < 0.75 THEN 1 ELSE 0 END
            + CASE WHEN dosage_rate < 0.60 THEN 1 ELSE 0 END
            + CASE WHEN followup_rate < 0.80 THEN 1 ELSE 0 END
            + CASE WHEN support_sla_rate < 0.80 THEN 1 ELSE 0 END
            + CASE WHEN fidelity_score < 70 THEN 1 ELSE 0 END
            + CASE WHEN data_refresh_days > 14 THEN 1 ELSE 0 END
        ) AS risk_score
    FROM v_school_operating_metrics
)
SELECT
    COUNT(*) AS eligible_students,
    SUM(activated_60d_flag) AS activated_students,
    ROUND(AVG(activated_60d_flag), 4) AS activation_rate,
    ROUND(AVG(dosage_target_months / 9.0), 4) AS dosage_target_rate,
    ROUND(
        AVG(CASE WHEN followup_score IS NOT NULL THEN 1.0 ELSE 0.0 END),
        4
    ) AS followup_completion_rate,
    ROUND(AVG(score_change), 2) AS avg_score_change,
    ROUND((SELECT support_sla_rate FROM ticket_kpis), 4)
        AS support_sla_rate,
    (SELECT COUNT(*) FROM school_risk WHERE risk_score >= 3)
        AS high_risk_schools
FROM v_student_summary;
