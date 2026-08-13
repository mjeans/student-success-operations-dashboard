WITH district_students AS (
    SELECT
        district_id,
        COUNT(*) AS students,
        AVG(activated_60d_flag) AS activation_rate,
        AVG(dosage_target_months / 9.0) AS dosage_rate,
        AVG(CASE WHEN followup_score IS NOT NULL THEN 1.0 ELSE 0.0 END)
            AS followup_rate,
        AVG(score_change) AS avg_score_change
    FROM v_student_summary
    GROUP BY district_id
),
district_operations AS (
    SELECT
        district_id,
        AVG(support_sla_rate) AS support_sla_rate,
        AVG(training_rate) AS training_rate,
        AVG(fidelity_score) AS fidelity_score,
        AVG(data_refresh_days) AS avg_refresh_days
    FROM v_school_operating_metrics
    GROUP BY district_id
)
SELECT
    dd.district_id,
    dd.district_name,
    dd.region,
    dd.locale,
    dd.implementation_tier,
    ds.students,
    ROUND(ds.activation_rate, 4) AS activation_rate,
    ROUND(ds.dosage_rate, 4) AS dosage_target_rate,
    ROUND(ds.followup_rate, 4) AS followup_completion_rate,
    ROUND(ds.avg_score_change, 2) AS avg_score_change,
    ROUND(dop.support_sla_rate, 4) AS support_sla_rate,
    ROUND(dop.training_rate, 4) AS training_rate,
    ROUND(dop.fidelity_score, 1) AS fidelity_score,
    ROUND(dop.avg_refresh_days, 1) AS avg_data_refresh_days,
    (
        CASE WHEN ds.activation_rate < 0.75 THEN 1 ELSE 0 END
        + CASE WHEN ds.dosage_rate < 0.60 THEN 1 ELSE 0 END
        + CASE WHEN ds.followup_rate < 0.80 THEN 1 ELSE 0 END
        + CASE WHEN dop.support_sla_rate < 0.80 THEN 1 ELSE 0 END
        + CASE WHEN dop.fidelity_score < 70 THEN 1 ELSE 0 END
        + CASE WHEN dop.avg_refresh_days > 14 THEN 1 ELSE 0 END
    ) AS risk_score
FROM dim_district AS dd
JOIN district_students AS ds
    ON dd.district_id = ds.district_id
JOIN district_operations AS dop
    ON dd.district_id = dop.district_id
ORDER BY risk_score DESC, ds.activation_rate ASC;
