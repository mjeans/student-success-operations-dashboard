PRAGMA foreign_keys = ON;

CREATE TABLE dim_district (
    district_id TEXT PRIMARY KEY,
    district_name TEXT NOT NULL,
    region TEXT NOT NULL,
    locale TEXT NOT NULL,
    implementation_tier TEXT NOT NULL,
    student_target INTEGER NOT NULL CHECK (student_target > 0)
);

CREATE TABLE dim_school (
    school_id TEXT PRIMARY KEY,
    district_id TEXT NOT NULL REFERENCES dim_district(district_id),
    school_name TEXT NOT NULL,
    grade_span TEXT NOT NULL,
    student_target INTEGER NOT NULL CHECK (student_target > 0)
);

CREATE TABLE dim_student (
    student_id TEXT PRIMARY KEY,
    school_id TEXT NOT NULL REFERENCES dim_school(school_id),
    grade_level INTEGER NOT NULL CHECK (grade_level BETWEEN 3 AND 8),
    enrollment_date TEXT NOT NULL
);

CREATE TABLE fact_engagement_monthly (
    student_id TEXT NOT NULL REFERENCES dim_student(student_id),
    month_start TEXT NOT NULL,
    active_flag INTEGER NOT NULL CHECK (active_flag IN (0, 1)),
    sessions INTEGER NOT NULL CHECK (sessions >= 0),
    minutes INTEGER NOT NULL CHECK (minutes >= 0),
    lessons_completed INTEGER NOT NULL CHECK (lessons_completed >= 0),
    PRIMARY KEY (student_id, month_start)
);

CREATE TABLE fact_assessment (
    assessment_id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL REFERENCES dim_student(student_id),
    assessment_window TEXT NOT NULL
        CHECK (assessment_window IN ('Baseline', 'Follow-up')),
    assessment_date TEXT NOT NULL,
    score REAL NOT NULL CHECK (score BETWEEN 0 AND 100)
);

CREATE TABLE fact_support_ticket (
    ticket_id TEXT PRIMARY KEY,
    school_id TEXT NOT NULL REFERENCES dim_school(school_id),
    opened_date TEXT NOT NULL,
    category TEXT NOT NULL,
    response_hours REAL NOT NULL CHECK (response_hours >= 0),
    satisfaction REAL NOT NULL CHECK (satisfaction BETWEEN 1 AND 5),
    resolved_flag INTEGER NOT NULL CHECK (resolved_flag IN (0, 1))
);

CREATE TABLE fact_implementation (
    school_id TEXT PRIMARY KEY REFERENCES dim_school(school_id),
    launch_on_time_flag INTEGER NOT NULL CHECK (launch_on_time_flag IN (0, 1)),
    staff_trained INTEGER NOT NULL CHECK (staff_trained >= 0),
    staff_expected INTEGER NOT NULL CHECK (staff_expected > 0),
    fidelity_score REAL NOT NULL CHECK (fidelity_score BETWEEN 0 AND 100),
    coach_checkins INTEGER NOT NULL CHECK (coach_checkins >= 0),
    data_refresh_days INTEGER NOT NULL CHECK (data_refresh_days >= 0)
);

CREATE INDEX idx_school_district
    ON dim_school (district_id);
CREATE INDEX idx_student_school
    ON dim_student (school_id);
CREATE INDEX idx_engagement_month
    ON fact_engagement_monthly (month_start);
CREATE INDEX idx_assessment_student_window
    ON fact_assessment (student_id, assessment_window);
CREATE INDEX idx_ticket_school
    ON fact_support_ticket (school_id);
