"""Render auditable, static SVG dashboard previews from committed CSV outputs.

Standard library only. No live services, JavaScript, invented chart data, or
edits to the analytic outputs. Risk highlights use the exported SQL flags,
never thresholds recomputed from rounded display values.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from html import escape
from pathlib import Path
from textwrap import wrap

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("executive-dashboard.svg", "implementation-monitor.svg", "outcomes-participation.svg")
FLAGS = ("missed_activation_target", "missed_dosage_target", "missed_followup_target",
         "missed_support_sla_target", "missed_fidelity_target", "stale_data_flag")


def number(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"Non-finite graphic input: {value!r}")
    return result


def pct(value: str | float) -> str:
    number(str(value))
    return f"{(Decimal(str(value)) * 100).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)}%"


def rows(root: Path, name: str) -> list[dict[str, str]]:
    with (root / "outputs" / name).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError(f"Missing CSV header: {name}")
        return list(reader)


def load(root: Path) -> dict:
    data = {
        "kpis": rows(root, "02_dashboard_kpis.csv"),
        "months": rows(root, "03_monthly_engagement.csv"),
        "districts": rows(root, "04_district_performance.csv"),
        "segments": rows(root, "05_segment_outcomes.csv"),
        "schools": rows(root, "06_implementation_risk.csv"),
        "actions": rows(root, "08_intervention_action_queue.csv"),
        "theme": json.loads((root / "powerbi/theme.json").read_text(encoding="utf-8")),
    }
    if len(data["kpis"]) != 1 or any(not data[k] for k in ("months", "districts", "segments", "schools")):
        raise ValueError("Expected one KPI row and nonempty cohort outputs.")
    data["kpis"] = data["kpis"][0]
    for key, ident in (("schools", "school_id"), ("districts", "district_id"), ("months", "month_start")):
        ids = [r[ident] for r in data[key]]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate {ident} in {key}")
    data["schools"].sort(key=lambda r: int(r["intervention_priority"]))
    data["months"].sort(key=lambda r: r["month_start"])
    per_school = Counter(r["school_id"] for r in data["actions"])
    action_keys = [(r["school_id"], r["driver_code"]) for r in data["actions"]]
    if len(action_keys) != len(set(action_keys)):
        raise ValueError("Duplicate school-driver action key")
    known = {r["school_id"] for r in data["schools"]}
    if set(per_school) - known:
        raise ValueError("Action queue contains an unknown school")
    for r in data["schools"]:
        flags = [int(r[f]) for f in FLAGS]
        if any(x not in (0, 1) for x in flags) or sum(flags) != int(r["risk_score"]):
            raise ValueError(f"Risk flags do not reconcile: {r['school_id']}")
        if per_school[r["school_id"]] != int(r["risk_score"]):
            raise ValueError(f"Action count does not reconcile: {r['school_id']}")
    high = sum(r["risk_band"] in ("Critical", "High") for r in data["schools"])
    if high != int(data["kpis"]["high_risk_schools"]):
        raise ValueError("Executive high-risk count does not reconcile")
    for key in ("months", "districts", "segments", "schools"):
        for r in data[key]:
            for name, value in r.items():
                if name.endswith("_rate") and not 0 <= number(value) <= 1:
                    raise ValueError(f"Rate outside [0, 1]: {name}")
    return data


class Page:
    """A self-contained SVG page with reusable, accessible visual components."""
    def __init__(self, title: str, subtitle: str, index: int, theme: dict):
        self.parts: list[str] = []
        self.ink = theme["foreground"]
        self.accent = theme["dataColors"][0]
        self.second = theme["dataColors"][4]
        self.bad = theme["bad"]
        self.bg = theme["background"]
        self.muted = theme["textClasses"]["label"]["color"]
        self.parts.append('<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1120" viewBox="0 0 1600 1120" role="img" aria-labelledby="title description">')
        self.parts.append(f'<title id="title">{escape(title)}</title><desc id="description">{escape(subtitle)} Static preview generated from committed synthetic CSV outputs; not a Power BI Desktop screenshot. Risk flags are inherited from SQL. Numeric labels and exclamation marks supplement color.</desc>')
        self.parts.append(f'<style>text{{font-family:"DejaVu Sans",Arial,sans-serif;fill:{self.ink}}}.muted{{fill:{self.muted}}}.accent{{fill:{self.accent}}}.bad{{fill:{self.bad}}}.light{{fill:white}}.bold{{font-weight:700}}.num{{font-variant-numeric:tabular-nums}}.grid{{stroke:{self.ink};stroke-opacity:.10}}.rule{{stroke:{self.ink};stroke-opacity:.18}}</style>')
        self.rect(0, 0, 1600, 1120, self.bg)
        self.rect(0, 0, 1600, 8, self.accent)
        self.text(44, 42, "MATTHEW JEANS  /  EDUCATION ANALYTICS", 14, "muted bold")
        self.text(1556, 42, "SYNTHETIC DATA  ·  STATIC PREVIEW", 14, "muted", "end")
        self.text(44, 98, title, 40, "bold")
        self.text(44, 133, subtitle, 18, "muted")
        self.text(44, 1093, "STUDENT SUCCESS OPERATIONS  /  Generated from saved SQL outputs", 14, "muted")
        self.text(1556, 1093, f"{index:02d} / 03", 15, "bold", "end")

    def rect(self, x, y, w, h, fill="white", radius=0, opacity=None):
        extra = f' opacity="{opacity}"' if opacity is not None else ""
        self.parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{radius}" fill="{fill}"{extra}/>')

    def text(self, x, y, value, size=18, cls="", anchor="start"):
        self.parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" class="{cls}" text-anchor="{anchor}">{escape(str(value))}</text>')

    def line(self, x1, y1, x2, y2, cls="rule", color=None, dash=False):
        attrs = f' stroke="{color}"' if color else f' class="{cls}"'
        if dash:
            attrs += ' stroke-dasharray="6 5"'
        self.parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"{attrs}/>')

    def paragraph(self, x, y, text, width=58, size=18, cls="muted", leading=28):
        for i, line in enumerate(wrap(text, width=width)):
            self.text(x, y + i * leading, line, size, cls)

    def panel(self, x, y, w, h, title, subtitle=""):
        self.rect(x, y, w, h, radius=12)
        self.text(x + 24, y + 36, title, 24, "bold")
        if subtitle:
            self.text(x + 24, y + 63, subtitle, 15, "muted")

    def cards(self, items, y=164, h=136):
        gap = 14
        w = (1512 - gap * (len(items) - 1)) / len(items)
        for i, (label, value, note, flag) in enumerate(items):
            x = 44 + i * (w + gap)
            self.rect(x, y, w, h, radius=10)
            self.rect(x + 20, y + 19, 30, 3, self.bad if flag else self.accent)
            self.text(x + 20, y + 46, label, 17, "muted")
            self.text(x + 20, y + 95, value, 43, "num bold bad" if flag else "num bold")
            self.text(x + 20, y + 119, note, 14, "muted")

    def trend(self, months, x, y, w, h):
        left, right, top, bottom = x + 56, x + w - 88, y + 100, y + h - 54
        self.line(x+24, y+60, x+49, y+60, color=self.accent)
        self.text(x+57, y+65, "Active students", 15, "muted")
        self.line(x+218, y+60, x+243, y+60, color=self.second, dash=True)
        self.text(x+251, y+65, "Dosage target met", 15, "muted")
        for tick in (0, 25, 50, 75, 100):
            yy = bottom - (bottom - top) * tick / 100
            self.line(left, yy, right, yy, "grid")
            self.text(left-10, yy+5, f"{tick}%", 14, "muted", "end")
        xs = [left+(right-left)*i/max(1,len(months)-1) for i in range(len(months))]
        for i, r in enumerate(months):
            self.text(xs[i], bottom+26, date.fromisoformat(r["month_start"]).strftime("%b"), 14, "muted", "middle")
        for key, col, dashed in (("active_rate", self.accent, False),("dosage_target_rate", self.second, True)):
            points = [(xx, bottom-number(r[key])*(bottom-top)) for xx,r in zip(xs,months)]
            dash = ' stroke-dasharray="7 5"' if dashed else ""
            coord = " ".join(f"{xx:.1f},{yy:.1f}" for xx,yy in points)
            self.parts.append(f'<polyline points="{coord}" fill="none" stroke="{col}" stroke-width="3"{dash}/>')
            for (xx, yy), r in zip(points, months):
                shape = f'<rect x="{xx-4:.1f}" y="{yy-4:.1f}" width="8" height="8" fill="{col}"/>' if dashed else f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="4" fill="{col}"/>'
                self.parts.append(f'<g><title>{escape(r["month_start"])} {escape(key)}: {pct(r[key])}</title>{shape}</g>')
            xx, yy = points[-1]
            self.text(xx+11, yy+(-8 if not dashed else 20), pct(months[-1][key]), 15, "bold")

    def bars(self, entries, x, y, w, h, max_value=1.0, target=None, percent=True):
        left, right, top, bottom = x + 188, x + w - 90, y + 104, y + h - 45
        ticks = (0, .25, .5, .75, 1) if percent else tuple(v / max_value for v in range(0, int(max_value) + 1, 5))
        for fraction in ticks:
            xx = left+(right-left)*fraction
            self.line(xx, top-14, xx, bottom+6, "grid")
            label = f"{fraction*max_value*100:g}%" if percent else f"{fraction*max_value:g}"
            self.text(xx, bottom+28, label, 13, "muted", "middle")
        if target is not None:
            xx=left+(right-left)*target/max_value
            self.line(xx, top-16, xx, bottom+6, color=self.ink, dash=True)
            self.text(xx, top-28, f"Target {pct(target)}", 14, "bold", "middle")
        step=(bottom-top)/max(1,len(entries))
        for i,(label,value) in enumerate(entries):
            yy=top+i*step
            self.text(left-14,yy+16,label,17,"", "end")
            self.rect(left, yy, (right-left)*value/max_value, 21, self.accent, 3)
            self.text(left+(right-left)*value/max_value+10, yy+16, pct(value) if percent else f"+{value:.2f}",16,"bold num")

    def finish(self, sources):
        self.text(44, 1063, "Sources: " + sources, 13, "muted")
        self.parts.append("</svg>")
        return "\n".join(self.parts) + "\n"


def executive(d: dict) -> str:
    k, schools, districts = d["kpis"], d["schools"], d["districts"]
    p=Page("Student success · Executive overview", "Where are students participating, and where should implementation support go first?",1,d["theme"])
    p.cards([
        ("Eligible students", f"{int(k['eligible_students']):,}",f"{len(districts)} districts · {len(schools)} schools",False),
        ("60-day activation",pct(k["activation_rate"]),"Eligible-student denominator",False),
        ("Dosage target met",pct(k["dosage_target_rate"]),"Student-month denominator",False),
        ("Follow-up complete",pct(k["followup_completion_rate"]),"Eligible-student denominator",False),
        ("Paired score change",f"+{number(k['avg_score_change']):.2f}","Descriptive, not causal",False),
        ("Support within 24h",pct(k["support_sla_rate"]),"Target ≥ 80% of tickets",number(k["support_sla_rate"])<.8),
    ])
    p.panel(44,324,724,385,"Participation over time")
    p.trend(d["months"],44,324,724,385)
    start=date.fromisoformat(d["months"][0]["month_start"]).strftime("%b %Y")
    end=date.fromisoformat(d["months"][-1]["month_start"]).strftime("%b %Y")
    p.text(744,358,f"{start} – {end}",13,"muted","end")
    p.panel(790,324,766,385,"Support responsiveness by district","Ticket-weighted rates; sorted from lowest to highest")
    p.bars([(r["district_name"],number(r["support_sla_rate"])) for r in sorted(districts,key=lambda r:number(r["support_sla_rate"]))],790,324,766,385,target=.8)
    p.panel(44,731,950,304,"Highest-priority schools","Ranking inherited from SQL; score = number of missed operating thresholds")
    for xx,label in ((68,"RANK"),(134,"SCHOOL"),(686,"SCORE / 6"),(833,"RISK BAND")):
        p.text(xx,823,label,14,"muted bold")
    for i,r in enumerate(schools[:5]):
        yy=858+i*33
        p.line(68,yy+12,970,yy+12,"grid")
        p.text(68,yy,r["intervention_priority"],17,"bold")
        p.text(134,yy,r["school_name"],18)
        p.text(727,yy,r["risk_score"],19,"bold num","middle")
        p.text(833,yy,r["risk_band"],17,"bold bad" if r["risk_band"]=="Critical" else "bold")
    p.panel(1016,731,540,304,"Focus the recovery effort")
    high=[r for r in schools if r["risk_band"] in ("Critical","High")]
    p.text(1040,828,str(len(high)),53,"bold accent")
    p.text(1100,815,"high-risk schools",22,"bold")
    critical=sum(r["risk_band"]=="Critical" for r in schools)
    p.text(1100,845,f"{critical} Critical · {len(high)-critical} High",17,"muted")
    lookup={r["district_id"]:r["district_name"] for r in districts}
    counts=Counter(lookup[r["district_id"]] for r in high)
    location="; ".join(f"{name}: {count}" for name,count in counts.most_common())
    p.paragraph(1040,886,location+".",42,17,leading=25)
    p.paragraph(1040,949,"Use the driver-level queue to separate service, implementation and data-feed problems.",43,17,leading=25)
    return p.finish("02_dashboard_kpis.csv · 03_monthly_engagement.csv · 04_district_performance.csv · 06_implementation_risk.csv")


def implementation(d: dict) -> str:
    s,a=d["schools"],d["actions"]
    critical=sum(r["risk_band"]=="Critical" for r in s)
    high=sum(r["risk_band"] in ("Critical","High") for r in s)
    training=sum(int(r["training_support_needed"]) for r in s)
    p=Page("Student success · Implementation monitor","Inspect the missed thresholds, then route the next action to the appropriate team.",2,d["theme"])
    p.cards([("High-risk schools",str(high),"Critical + High bands",False),("Critical schools",str(critical),"Four or more scored flags",True),("Scored action rows",str(len(a)),"One row per school and driver",False),("Schools with actions",str(len({r['school_id'] for r in a})),"Distinct schools, not action rows",False)])
    p.panel(44,324,1512,380,"School-level risk drivers","Top eight by intervention priority · ! = exported missed-target flag · values retain their own units")
    columns=[("Activation", "activation_rate", FLAGS[0],"rate"),("Dosage", "dosage_target_rate", FLAGS[1],"rate"),("Follow-up", "followup_completion_rate", FLAGS[2],"rate"),("Support / 24h", "support_sla_rate", FLAGS[3],"rate"),("Fidelity", "fidelity_score", FLAGS[4],"score"),("Refresh age", "data_refresh_days", FLAGS[5],"days")]
    p.text(68,420,"SCHOOL",14,"muted bold")
    centers=[535,690,845,1000,1155,1310]
    for xx,(label,_,_,_) in zip(centers,columns):
        p.text(xx,420,label,15,"muted bold","middle")
    p.text(1455,420,"SCORE / 6",14,"muted bold","middle")
    for i,r in enumerate(s[:8]):
        yy=453+i*31
        p.line(68,yy+12,1532,yy+12,"grid")
        p.text(68,yy,f"{r['intervention_priority']}. {r['school_name']}",17,"bold" if i==0 else "")
        for xx,(_,key,flag,kind) in zip(centers,columns):
            value=pct(r[key]) if kind=="rate" else (f"{number(r[key]):.1f} / 100" if kind=="score" else f"{int(r[key])} days")
            flagged=int(r[flag])==1
            if flagged:
                p.rect(xx-66,yy-20,132,27,p.bad,5,.09)
            p.text(xx,yy,value+(" !" if flagged else ""),16,"bold bad" if flagged else "num","middle")
        p.text(1455,yy,r["risk_score"],19,"bold","middle")
    active={r["school_id"] for r in a}
    lead=next((r for r in s if r["school_id"] in active),None)
    title=f"Action detail · {lead['school_name']}" if lead else "Action detail · No missed scored thresholds"
    p.panel(44,726,1000,309,title,"Observed values and targets come directly from the action queue")
    for xx,label in ((68,"DRIVER"),(386,"OBSERVED"),(539,"TARGET"),(704,"SUGGESTED OWNER")):
        p.text(xx,825,label,14,"muted bold")
    selected=sorted([r for r in a if lead and r["school_id"]==lead["school_id"]],key=lambda r:int(r["driver_order"]))
    aliases={"DOSAGE":"Dosage target met","FOLLOWUP":"Follow-up complete","SUPPORT_SLA":"Support within 24h","FIDELITY":"Fidelity","DATA_FRESHNESS":"Refresh age","ACTIVATION":"60-day activation"}
    for i,r in enumerate(selected):
        yy=858+i*28
        is_rate=r["metric_unit"]=="proportion"
        observed=pct(r["observed_value"]) if is_rate else f"{number(r['observed_value']):g}"
        target=pct(r["target_value"]) if is_rate else f"{number(r['target_value']):g}"
        if r["metric_unit"]=="days": observed+=" days"; target+=" days"
        target=("≥ " if r["failure_operator"]=="<" else "≤ ")+target
        p.text(68,yy,aliases.get(r["driver_code"],r["driver_label"]),17)
        p.text(386,yy,observed,17,"bold num")
        p.text(539,yy,target,17,"num")
        p.text(704,yy,r["suggested_owner"],17)
    p.panel(1066,726,490,309,"Read the score carefully")
    p.paragraph(1090,802,f"Training support is flagged at {training} schools. It is context, not a seventh risk point.",38,18,leading=27)
    p.paragraph(1090,900,"Verify stale data before acting. Owners and review cadence are proposals, not assigned work.",38,18,leading=27)
    p.text(1090,1006,"Risk rules are not a validated prediction.",15,"bold")
    return p.finish("06_implementation_risk.csv · 08_intervention_action_queue.csv · docs/action-queue.md")


def outcomes(d: dict) -> str:
    k=d["kpis"]
    p=Page("Student success · Outcomes & participation","Keep descriptive score change alongside cohort size and follow-up completeness.",3,d["theme"])
    missing=1-number(k["followup_completion_rate"])
    p.cards([("Eligible students",f"{int(k['eligible_students']):,}","Total cohort, not paired sample",False),("Follow-up complete",pct(k["followup_completion_rate"]),"Share of eligible students",False),("Missing follow-up",pct(missing),"Completeness gap, not zero growth",True),("Paired score change",f"+{number(k['avg_score_change']):.2f}","Not a causal program effect",False)])
    grades=[r for r in d["segments"] if r["segment_dimension"]=="Grade level"]
    p.panel(44,324,724,385,"Average paired score change by grade","Score points · within-student change among observed pairs")
    values=[number(r["avg_score_change"]) for r in grades]
    if any(v<0 for v in values):
        raise ValueError("Negative grade changes require a signed-axis layout; do not silently clip.")
    upper=max(15,math.ceil(max(values,default=0)/5)*5)
    p.bars([(r["segment"],number(r["avg_score_change"])) for r in grades],44,324,724,385,max_value=upper,percent=False)
    p.panel(790,324,766,385,"Monthly participation")
    p.trend(d["months"],790,324,766,385)
    p.panel(44,731,950,304,"Completeness and change by segment","Cohort n is not the paired-score denominator; dimensions overlap")
    for xx,label in ((68,"SEGMENT"),(454,"COHORT N"),(625,"FOLLOW-UP"),(826,"PAIRED CHANGE")):
        p.text(xx,821,label,14,"muted bold")
    selected=[r for r in d["segments"] if r["segment_dimension"]=="District locale"]+[r for r in d["segments"] if r["segment_dimension"]=="Implementation tier"]
    for i,r in enumerate(selected):
        yy=850+i*25
        if i==4:p.line(68,yy-18,970,yy-18)
        label=r["segment"]
        p.text(68,yy,label,16)
        p.text(520,yy,f"{int(r['students']):,}",16,"num","end")
        p.text(699,yy,pct(r["followup_completion_rate"]),16,"num","end")
        p.text(950,yy,f"+{number(r['avg_score_change']):.2f}",16,"bold num","end")
    p.panel(1016,731,540,304,"What the evidence does not say")
    p.paragraph(1040,807,"Observed change is not program impact. There is no untreated comparison group in this case study.",45,18,leading=28)
    p.paragraph(1040,914,"Do not subtract the separate baseline and follow-up averages: their observed samples can differ. Use paired change.",45,18,leading=28)
    return p.finish("02_dashboard_kpis.csv · 03_monthly_engagement.csv · 05_segment_outcomes.csv")


def render(root: Path = ROOT) -> dict[str, str]:
    d=load(root)
    return dict(zip(NAMES,(executive(d),implementation(d),outcomes(d))))


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true",help="Fail if committed SVG previews are stale; do not write files")
    parser.add_argument("--root",type=Path,default=ROOT,help="Repository root (primarily for testing)")
    args=parser.parse_args()
    try:
        graphics=render(args.root)
        stale=[]
        for name,content in graphics.items():
            path=args.root/"assets"/name
            if args.check:
                if not path.exists() or path.read_text(encoding="utf-8")!=content: stale.append(name)
            else:
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(content,encoding="utf-8",newline="\n")
        if stale:
            print("Stale previews: "+", ".join(stale)+"; run python scripts/render_previews.py",file=sys.stderr)
            return 1
        print("Verified 3 source-driven SVG previews." if args.check else "Rendered 3 source-driven SVG previews.")
        return 0
    except (ValueError,KeyError,OSError) as exc:
        print(f"Preview validation failed: {exc}",file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
