"""Generate deterministic synthetic data for the dashboard case study."""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "build" / "generated"
SEED = 20260812

DISTRICTS = [
    ("D001", "Cedar Valley", "North", "Suburban", "Early adopter", 0.84),
    ("D002", "Harbor Point", "East", "Urban", "Standard", 0.78),
    ("D003", "Northstar", "North", "Rural", "Intensive support", 0.68),
    ("D004", "Pine Ridge", "West", "Town", "Standard", 0.65),
    ("D005", "Riverbend", "South", "Suburban", "Early adopter", 0.80),
    ("D006", "Summit Plains", "West", "Rural", "Intensive support", 0.57),
    ("D007", "Vista Grove", "South", "Urban", "Standard", 0.73),
    ("D008", "Willow Creek", "East", "Town", "Standard", 0.70),
]

MONTHS = [
    date(2025, 9, 1),
    date(2025, 10, 1),
    date(2025, 11, 1),
    date(2025, 12, 1),
    date(2026, 1, 1),
    date(2026, 2, 1),
    date(2026, 3, 1),
    date(2026, 4, 1),
    date(2026, 5, 1),
]


def write_csv(name: str, headers: list[str], rows: list[list[object]]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def main() -> None:
    rng = random.Random(SEED)

    district_rows: list[list[object]] = []
    school_rows: list[list[object]] = []
    student_rows: list[list[object]] = []
    engagement_rows: list[list[object]] = []
    assessment_rows: list[list[object]] = []
    ticket_rows: list[list[object]] = []
    implementation_rows: list[list[object]] = []

    student_profiles: list[dict[str, object]] = []
    school_profiles: list[dict[str, object]] = []

    for district_id, name, region, locale, tier, adoption in DISTRICTS:
        district_rows.append(
            [district_id, name, region, locale, tier, 400]
        )
        for school_number in range(1, 5):
            school_id = f"S{int(district_id[1:]):03d}{school_number}"
            school_name = f"{name} School {school_number}"
            grade_span = "3-5" if school_number <= 2 else "6-8"
            school_modifier = rng.uniform(-0.055, 0.055)
            school_profiles.append(
                {
                    "school_id": school_id,
                    "district_id": district_id,
                    "adoption": adoption,
                    "modifier": school_modifier,
                    "tier": tier,
                }
            )
            school_rows.append(
                [school_id, district_id, school_name, grade_span, 100]
            )

            expected_staff = rng.randint(18, 32)
            support_penalty = 0.10 if tier == "Intensive support" else 0.0
            trained_rate = clamp(
                adoption + school_modifier - support_penalty + rng.uniform(0.03, 0.13),
                0.48,
                0.99,
            )
            staff_trained = round(expected_staff * trained_rate)
            fidelity = round(
                clamp(
                    42 + 52 * adoption + 45 * school_modifier
                    - 12 * support_penalty + rng.gauss(0, 4),
                    42,
                    98,
                ),
                1,
            )
            implementation_rows.append(
                [
                    school_id,
                    1 if rng.random() < adoption + 0.08 else 0,
                    staff_trained,
                    expected_staff,
                    fidelity,
                    rng.randint(2, 8),
                    max(0, round(rng.gauss(4 + 18 * (1 - adoption), 3))),
                ]
            )

            for student_number in range(1, 101):
                student_id = (
                    f"ST{int(district_id[1:]):03d}{school_number}"
                    f"{student_number:03d}"
                )
                grade_low, grade_high = (3, 5) if grade_span == "3-5" else (6, 8)
                grade = rng.randint(grade_low, grade_high)
                enrollment_date = date(2025, 8, 15) + timedelta(
                    days=rng.randint(0, 35)
                )
                student_rows.append(
                    [
                        student_id,
                        school_id,
                        grade,
                        enrollment_date.isoformat(),
                    ]
                )

                student_propensity = rng.gauss(0, 0.10)
                baseline = clamp(
                    rng.gauss(50 + 1.1 * (grade - 5), 12)
                    + 3.0 * school_modifier,
                    12,
                    88,
                )
                student_profiles.append(
                    {
                        "student_id": student_id,
                        "school_id": school_id,
                        "district_id": district_id,
                        "adoption": adoption,
                        "school_modifier": school_modifier,
                        "student_propensity": student_propensity,
                        "baseline": baseline,
                    }
                )

    cumulative_minutes: dict[str, int] = {}
    active_months: dict[str, int] = {}
    for profile in student_profiles:
        total_minutes = 0
        months_active = 0
        for month_index, month_start in enumerate(MONTHS):
            ramp = [0.00, 0.035, 0.055, 0.035, 0.075, 0.095, 0.11, 0.105, 0.09][
                month_index
            ]
            winter_dip = -0.055 if month_start.month == 12 else 0.0
            probability = clamp(
                float(profile["adoption"])
                + float(profile["school_modifier"])
                + float(profile["student_propensity"])
                + ramp
                + winter_dip,
                0.18,
                0.97,
            )
            active = int(rng.random() < probability)
            if active:
                mean_minutes = (
                    62
                    + 28 * float(profile["adoption"])
                    + 95 * float(profile["school_modifier"])
                    + 3 * month_index
                )
                minutes = max(8, round(rng.gauss(mean_minutes, 29)))
                sessions = max(1, round(minutes / rng.uniform(17, 28)))
                lessons = max(1, round(minutes / rng.uniform(22, 36)))
                months_active += 1
                total_minutes += minutes
            else:
                minutes = 0
                sessions = 0
                lessons = 0
            engagement_rows.append(
                [
                    profile["student_id"],
                    month_start.isoformat(),
                    active,
                    sessions,
                    minutes,
                    lessons,
                ]
            )
        cumulative_minutes[str(profile["student_id"])] = total_minutes
        active_months[str(profile["student_id"])] = months_active

    for index, profile in enumerate(student_profiles, start=1):
        student_id = str(profile["student_id"])
        baseline = round(float(profile["baseline"]), 1)
        assessment_rows.append(
            [
                f"A{index:05d}B",
                student_id,
                "Baseline",
                "2025-09-15",
                baseline,
            ]
        )
        followup_probability = clamp(
            0.52
            + 0.045 * active_months[student_id]
            + 0.08 * float(profile["adoption"]),
            0.55,
            0.97,
        )
        if rng.random() < followup_probability:
            change = (
                1.2
                + 0.0095 * cumulative_minutes[student_id]
                + 0.30 * active_months[student_id]
                + rng.gauss(0, 4.4)
            )
            followup = round(clamp(baseline + change, 5, 100), 1)
            assessment_rows.append(
                [
                    f"A{index:05d}F",
                    student_id,
                    "Follow-up",
                    "2026-05-22",
                    followup,
                ]
            )

    ticket_counter = 0
    categories = [
        "Access",
        "Data sync",
        "Instructional workflow",
        "Reporting",
        "Training",
    ]
    for school in school_profiles:
        adoption = float(school["adoption"]) + float(school["modifier"])
        for month_start in MONTHS:
            expected = 1.2 + 3.6 * (1 - adoption)
            ticket_count = max(0, round(rng.gauss(expected, 1.1)))
            for _ in range(ticket_count):
                ticket_counter += 1
                response_hours = round(
                    max(0.5, rng.gauss(9 + 36 * (1 - adoption), 8)), 1
                )
                satisfaction = round(
                    clamp(5.1 - response_hours / 17 + rng.gauss(0, 0.45), 1, 5),
                    1,
                )
                opened = month_start + timedelta(days=rng.randint(0, 26))
                ticket_rows.append(
                    [
                        f"T{ticket_counter:05d}",
                        school["school_id"],
                        opened.isoformat(),
                        rng.choice(categories),
                        response_hours,
                        satisfaction,
                        int(rng.random() < 0.96),
                    ]
                )

    write_csv(
        "dim_district.csv",
        [
            "district_id",
            "district_name",
            "region",
            "locale",
            "implementation_tier",
            "student_target",
        ],
        district_rows,
    )
    write_csv(
        "dim_school.csv",
        [
            "school_id",
            "district_id",
            "school_name",
            "grade_span",
            "student_target",
        ],
        school_rows,
    )
    write_csv(
        "dim_student.csv",
        [
            "student_id",
            "school_id",
            "grade_level",
            "enrollment_date",
        ],
        student_rows,
    )
    write_csv(
        "fact_engagement_monthly.csv",
        [
            "student_id",
            "month_start",
            "active_flag",
            "sessions",
            "minutes",
            "lessons_completed",
        ],
        engagement_rows,
    )
    write_csv(
        "fact_assessment.csv",
        [
            "assessment_id",
            "student_id",
            "assessment_window",
            "assessment_date",
            "score",
        ],
        assessment_rows,
    )
    write_csv(
        "fact_support_ticket.csv",
        [
            "ticket_id",
            "school_id",
            "opened_date",
            "category",
            "response_hours",
            "satisfaction",
            "resolved_flag",
        ],
        ticket_rows,
    )
    write_csv(
        "fact_implementation.csv",
        [
            "school_id",
            "launch_on_time_flag",
            "staff_trained",
            "staff_expected",
            "fidelity_score",
            "coach_checkins",
            "data_refresh_days",
        ],
        implementation_rows,
    )

    print(
        f"Generated {len(student_rows):,} students, "
        f"{len(engagement_rows):,} student-months, "
        f"{len(assessment_rows):,} assessments, and "
        f"{len(ticket_rows):,} support tickets."
    )


if __name__ == "__main__":
    main()
