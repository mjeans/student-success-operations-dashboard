WITH scored AS (
    SELECT
        som.*,
        (
            CASE WHEN activation_rate < 0.75 THEN 1 ELSE 0 END
            + CASE WHEN dosage_rate < 0.60 THEN 1 ELSE 0 END
            + CASE WHEN followup_rate < 0.80 THEN 1 ELSE 0 END
            + CASE WHEN support_sla_rate < 0.80 THEN 1 ELSE 0 END
            + CASE WHEN fidelity_score < 70 THEN 1 ELSE 0 END
            + CASE WHEN data_refresh_days > 14 THEN 1 ELSE 0 END
        ) AS risk_score
    FROM v_school_operating_metrics AS som
)
SELECT
    RANK() OVER (
        ORDER BY risk_score DESC, activation_rate ASC, school_id
    ) AS intervention_priority,
    school_id,
    school_name,
    district_id,
    students,
    ROUND(activation_rate, 4) AS activation_rate,
    ROUND(dosage_rate, 4) AS dosage_target_rate,
    ROUND(followup_rate, 4) AS followup_completion_rate,
    ROUND(support_sla_rate, 4) AS support_sla_rate,
    ROUND(training_rate, 4) AS training_rate,
    ROUND(fidelity_score, 1) AS fidelity_score,
    data_refresh_days,
    risk_score,
    CASE
        WHEN risk_score >= 4 THEN 'Critical'
        WHEN risk_score = 3 THEN 'High'
        WHEN risk_score = 2 THEN 'Watch'
        ELSE 'Stable'
    END AS risk_band
FROM scored
ORDER BY intervention_priority, school_id;
