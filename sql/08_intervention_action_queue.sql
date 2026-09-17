-- Grain: one row per school and failed SCORED driver, not one row per school.
-- Use unrounded values for decisions. Training is context, never a seventh driver.
SELECT
    risk.intervention_priority,
    risk.school_id,
    risk.school_name,
    risk.district_id,
    risk.students,
    risk.risk_band,
    risk.risk_score,
    driver.driver_order,
    driver.driver_code,
    driver.driver_label,
    driver.observed_value,
    driver.target_value,
    driver.metric_unit,
    driver.failure_operator,
    driver.recommended_first_action,
    driver.suggested_owner,
    CASE risk.risk_band
        WHEN 'Critical' THEN 'Twice weekly'
        WHEN 'High' THEN 'Weekly'
        WHEN 'Watch' THEN 'Every two weeks'
        ELSE 'Monthly'
    END AS suggested_review_cadence,
    risk.training_rate,
    risk.training_support_needed,
    risk.stale_data_flag
FROM v_school_implementation_risk AS risk
JOIN v_school_risk_drivers AS driver ON risk.school_id = driver.school_id
WHERE driver.target_missed = 1
ORDER BY risk.intervention_priority, risk.school_id, driver.driver_order;
