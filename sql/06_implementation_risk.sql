-- Preserve the original columns and ordering; append explicit driver flags.
SELECT
    intervention_priority,
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
    risk_band,
    missed_activation_target,
    missed_dosage_target,
    missed_followup_target,
    missed_support_sla_target,
    missed_fidelity_target,
    stale_data_flag,
    training_support_needed
FROM v_school_implementation_risk
ORDER BY intervention_priority, school_id;
