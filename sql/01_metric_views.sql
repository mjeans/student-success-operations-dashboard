DROP VIEW IF EXISTS v_student_engagement;
CREATE VIEW v_student_engagement AS
SELECT
    student_id,
    SUM(minutes) AS total_minutes,
    SUM(sessions) AS total_sessions,
    SUM(lessons_completed) AS total_lessons,
    SUM(active_flag) AS active_months,
    SUM(CASE WHEN minutes >= 60 THEN 1 ELSE 0 END) AS dosage_target_months,
    MAX(
        CASE
            WHEN month_start IN ('2025-09-01', '2025-10-01')
                AND active_flag = 1
            THEN 1
            ELSE 0
        END
    ) AS activated_60d_flag
FROM fact_engagement_monthly
GROUP BY student_id;

DROP VIEW IF EXISTS v_student_outcomes;
CREATE VIEW v_student_outcomes AS
SELECT
    student_id,
    MAX(CASE WHEN assessment_window = 'Baseline' THEN score END)
        AS baseline_score,
    MAX(CASE WHEN assessment_window = 'Follow-up' THEN score END)
        AS followup_score,
    MAX(CASE WHEN assessment_window = 'Follow-up' THEN score END)
        - MAX(CASE WHEN assessment_window = 'Baseline' THEN score END)
        AS score_change
FROM fact_assessment
GROUP BY student_id;

DROP VIEW IF EXISTS v_student_summary;
CREATE VIEW v_student_summary AS
SELECT
    st.student_id,
    st.school_id,
    sc.district_id,
    st.grade_level,
    en.total_minutes,
    en.total_sessions,
    en.total_lessons,
    en.active_months,
    en.dosage_target_months,
    en.activated_60d_flag,
    ou.baseline_score,
    ou.followup_score,
    ou.score_change
FROM dim_student AS st
JOIN dim_school AS sc
    ON st.school_id = sc.school_id
JOIN v_student_engagement AS en
    ON st.student_id = en.student_id
LEFT JOIN v_student_outcomes AS ou
    ON st.student_id = ou.student_id;

DROP VIEW IF EXISTS v_school_operating_metrics;
CREATE VIEW v_school_operating_metrics AS
WITH student_metrics AS (
    SELECT
        school_id,
        COUNT(*) AS students,
        AVG(activated_60d_flag) AS activation_rate,
        AVG(dosage_target_months / 9.0) AS dosage_rate,
        AVG(CASE WHEN followup_score IS NOT NULL THEN 1.0 ELSE 0.0 END)
            AS followup_rate,
        AVG(score_change) AS avg_score_change
    FROM v_student_summary
    GROUP BY school_id
),
ticket_metrics AS (
    SELECT
        school_id,
        COUNT(*) AS tickets,
        AVG(CASE WHEN response_hours <= 24 THEN 1.0 ELSE 0.0 END)
            AS support_sla_rate,
        AVG(response_hours) AS avg_response_hours,
        AVG(satisfaction) AS avg_satisfaction
    FROM fact_support_ticket
    GROUP BY school_id
)
SELECT
    sc.school_id,
    sc.school_name,
    sc.district_id,
    sm.students,
    sm.activation_rate,
    sm.dosage_rate,
    sm.followup_rate,
    sm.avg_score_change,
    COALESCE(tm.tickets, 0) AS tickets,
    COALESCE(tm.support_sla_rate, 1.0) AS support_sla_rate,
    COALESCE(tm.avg_response_hours, 0.0) AS avg_response_hours,
    tm.avg_satisfaction,
    fi.launch_on_time_flag,
    fi.staff_trained * 1.0 / fi.staff_expected AS training_rate,
    fi.fidelity_score,
    fi.coach_checkins,
    fi.data_refresh_days
FROM dim_school AS sc
JOIN student_metrics AS sm
    ON sc.school_id = sm.school_id
JOIN fact_implementation AS fi
    ON sc.school_id = fi.school_id
LEFT JOIN ticket_metrics AS tm
    ON sc.school_id = tm.school_id;
