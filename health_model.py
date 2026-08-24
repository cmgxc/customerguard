"""
CustomerGuard - Customer Health Model (Phase 1)
================================================
An applied project modeling the customer-health analysis a CSM / TAM runs on
their book of business, themed around a security SaaS (a vulnerability-management
platform sold to businesses).

This module does three things:
  1. Defines a realistic set of mock customer accounts.
  2. Scores each account's health (0-100) from weighted usage + security signals.
  3. Flags churn risks and expansion (upsell) opportunities, each with a
     plain-English recommended action.

Built with AI-assisted development as a learning project. Data is synthetic so
the scoring logic is the focus.

Run:  python health_model.py
Output: writes accounts.json (consumed by the dashboard) and prints a summary.
"""

import json
from datetime import date


# ---------------------------------------------------------------------------
# 1. MOCK DATA
# ---------------------------------------------------------------------------
# Each account carries the signals a real CSM/TAM watches. For a security SaaS
# those fall into three buckets:
#   - Commercial: plan tier, renewal timing, seats licensed vs. active
#   - Engagement: logins, scans run (is the product actually being used?)
#   - Security posture / outcomes: open critical vulns, % findings remediated
#
# "as_of" is the reference date we measure "days until renewal" against.
AS_OF = date(2026, 8, 1)

ACCOUNTS = [
    {
        "name": "Meridian Health Systems", "tier": "Enterprise", "arr": 145000,
        "seats_licensed": 50, "seats_active": 47, "logins_last_30d": 210,
        "scans_last_30d": 88, "open_critical_vulns": 3, "pct_remediated": 91,
        "support_tickets_30d": 2, "days_to_renewal": 210,
    },
    {
        "name": "Coastal Credit Union", "tier": "Enterprise", "arr": 120000,
        "seats_licensed": 40, "seats_active": 12, "logins_last_30d": 22,
        "scans_last_30d": 6, "open_critical_vulns": 14, "pct_remediated": 38,
        "support_tickets_30d": 9, "days_to_renewal": 41,
    },
    {
        "name": "Vantage Logistics", "tier": "Growth", "arr": 48000,
        "seats_licensed": 20, "seats_active": 19, "logins_last_30d": 140,
        "scans_last_30d": 51, "open_critical_vulns": 1, "pct_remediated": 95,
        "support_tickets_30d": 1, "days_to_renewal": 95,
    },
    {
        "name": "Brightwave Media", "tier": "Growth", "arr": 39000,
        "seats_licensed": 15, "seats_active": 5, "logins_last_30d": 14,
        "scans_last_30d": 3, "open_critical_vulns": 8, "pct_remediated": 44,
        "support_tickets_30d": 6, "days_to_renewal": 68,
    },
    {
        "name": "Ironclad Manufacturing", "tier": "Enterprise", "arr": 165000,
        "seats_licensed": 60, "seats_active": 58, "logins_last_30d": 260,
        "scans_last_30d": 110, "open_critical_vulns": 5, "pct_remediated": 87,
        "support_tickets_30d": 3, "days_to_renewal": 150,
    },
    {
        "name": "Summit Financial Advisors", "tier": "Growth", "arr": 42000,
        "seats_licensed": 18, "seats_active": 17, "logins_last_30d": 120,
        "scans_last_30d": 44, "open_critical_vulns": 2, "pct_remediated": 89,
        "support_tickets_30d": 0, "days_to_renewal": 33,
    },
    {
        "name": "Pinnacle Retail Group", "tier": "Starter", "arr": 14000,
        "seats_licensed": 10, "seats_active": 3, "logins_last_30d": 9,
        "scans_last_30d": 2, "open_critical_vulns": 11, "pct_remediated": 29,
        "support_tickets_30d": 4, "days_to_renewal": 22,
    },
    {
        "name": "Northstar Energy", "tier": "Enterprise", "arr": 132000,
        "seats_licensed": 45, "seats_active": 44, "logins_last_30d": 198,
        "scans_last_30d": 79, "open_critical_vulns": 4, "pct_remediated": 84,
        "support_tickets_30d": 2, "days_to_renewal": 300,
    },
    {
        "name": "Cedar Point Software", "tier": "Growth", "arr": 51000,
        "seats_licensed": 20, "seats_active": 20, "logins_last_30d": 175,
        "scans_last_30d": 64, "open_critical_vulns": 0, "pct_remediated": 98,
        "support_tickets_30d": 1, "days_to_renewal": 58,
    },
    {
        "name": "Harbor Point Insurance", "tier": "Growth", "arr": 45000,
        "seats_licensed": 18, "seats_active": 8, "logins_last_30d": 30,
        "scans_last_30d": 10, "open_critical_vulns": 6, "pct_remediated": 55,
        "support_tickets_30d": 5, "days_to_renewal": 25,
    },
    {
        "name": "Apex Biotech", "tier": "Enterprise", "arr": 158000,
        "seats_licensed": 55, "seats_active": 41, "logins_last_30d": 150,
        "scans_last_30d": 60, "open_critical_vulns": 7, "pct_remediated": 72,
        "support_tickets_30d": 4, "days_to_renewal": 120,
    },
    {
        "name": "Lakeside Education", "tier": "Starter", "arr": 16000,
        "seats_licensed": 12, "seats_active": 11, "logins_last_30d": 95,
        "scans_last_30d": 33, "open_critical_vulns": 1, "pct_remediated": 90,
        "support_tickets_30d": 0, "days_to_renewal": 47,
    },
]


# ---------------------------------------------------------------------------
# 2. HEALTH SCORING
# ---------------------------------------------------------------------------
# The score is a weighted blend of four sub-scores, each normalized to 0-100.
# The weights encode a point of view about what predicts churn vs. retention
# for a security SaaS. That point of view IS the CSM/TAM thinking, so the model
# is intentionally transparent rather than a black box.
#
#   Adoption (35%)  - are licensed seats actually being used? The #1 leading
#                     indicator of renewal in seat-based SaaS.
#   Engagement (25%)- logins and scans: is the product part of their routine?
#   Security Outcome(25%) - are they getting VALUE (remediating findings, low
#                     open critical exposure)? For a security tool, outcomes are
#                     the product's whole reason to exist.
#   Support Signal (15%) - excessive tickets can signal friction/frustration.
#
# Renewal proximity doesn't change the score itself but sharpens urgency: a
# mediocre score is a bigger deal when renewal is 30 days out than 300.

WEIGHTS = {"adoption": 0.35, "engagement": 0.25, "security": 0.25, "support": 0.15}


def _clamp(value, low=0, high=100):
    return max(low, min(high, value))


def adoption_score(a):
    """Active/licensed seat ratio, scaled to 0-100."""
    if a["seats_licensed"] == 0:
        return 0
    return _clamp(round(a["seats_active"] / a["seats_licensed"] * 100))


def engagement_score(a):
    """
    Blend of login intensity and scan activity, normalized per active seat so
    small and large accounts are compared fairly. Benchmarks (logins/seat >= 4
    per 30d and scans/seat >= 1.5 per 30d) represent a 'healthy usage' target.
    """
    seats = max(a["seats_active"], 1)
    logins_per_seat = a["logins_last_30d"] / seats
    scans_per_seat = a["scans_last_30d"] / seats
    login_component = _clamp(logins_per_seat / 4 * 100)   # 4+/seat -> full marks
    scan_component = _clamp(scans_per_seat / 1.5 * 100)   # 1.5+/seat -> full marks
    return round(0.5 * login_component + 0.5 * scan_component)


def security_outcome_score(a):
    """
    Are they getting security value? Reward high remediation rates; penalize a
    backlog of open critical vulnerabilities (the thing the product exists to
    reduce). 10+ open criticals zeroes out the exposure component.
    """
    remediation_component = _clamp(a["pct_remediated"])
    exposure_penalty = _clamp(a["open_critical_vulns"] / 10 * 100)
    exposure_component = _clamp(100 - exposure_penalty)
    return round(0.6 * remediation_component + 0.4 * exposure_component)


def support_score(a):
    """
    Some tickets are healthy engagement; a spike suggests friction. 0-2 tickets
    is ideal; each additional ticket past 2 costs points.
    """
    tickets = a["support_tickets_30d"]
    if tickets <= 2:
        return 100
    return _clamp(100 - (tickets - 2) * 15)


def health_score(a):
    subs = {
        "adoption": adoption_score(a),
        "engagement": engagement_score(a),
        "security": security_outcome_score(a),
        "support": support_score(a),
    }
    total = sum(subs[k] * WEIGHTS[k] for k in WEIGHTS)
    return round(total), subs


def status_from_score(score):
    if score >= 75:
        return "Healthy"
    if score >= 50:
        return "At-Risk"
    return "Critical"


# ---------------------------------------------------------------------------
# 3. RISK & EXPANSION FLAGS  (+ recommended action)
# ---------------------------------------------------------------------------
# This is the translation-to-business-value layer: don't just score, tell the
# CSM what to DO. Each account gets the single most useful recommended action.

def recommended_action(a, score, subs):
    renewal_soon = a["days_to_renewal"] <= 45
    seat_ratio = a["seats_active"] / max(a["seats_licensed"], 1)

    # Highest-priority: at-risk AND renewing soon -> save motion
    if score < 60 and renewal_soon:
        return ("churn", f"Urgent save: score {score} with renewal in "
                f"{a['days_to_renewal']} days. Schedule an executive check-in and "
                f"build a get-well plan.")
    # Security value not landing -> the product isn't delivering its core promise
    if subs["security"] < 55:
        return ("churn", f"Value at risk: {a['open_critical_vulns']} open critical "
                f"vulns and only {a['pct_remediated']}% remediated. Run a posture "
                f"review to re-establish value.")
    # Low adoption -> leading churn indicator
    if subs["adoption"] < 50:
        return ("churn", f"Low adoption: only {a['seats_active']} of "
                f"{a['seats_licensed']} seats active. Drive an enablement / "
                f"re-onboarding push.")
    # Expansion: healthy AND nearly out of seats -> upsell headroom
    if score >= 75 and seat_ratio >= 0.9:
        return ("expansion", f"Expansion signal: {round(seat_ratio*100)}% seat "
                f"utilization and strong health. Explore a seat upsell or tier "
                f"upgrade.")
    # Healthy, stable
    if score >= 75:
        return ("healthy", "Healthy and steady. Maintain cadence; good candidate "
                "for a reference or case study.")
    # Middle of the road
    return ("watch", f"Monitor: score {score}. Reinforce adoption and check in "
            f"before renewal ({a['days_to_renewal']} days out).")


# ---------------------------------------------------------------------------
# 4. BUILD + OUTPUT
# ---------------------------------------------------------------------------
def build_portfolio():
    accounts = []
    for a in ACCOUNTS:
        score, subs = health_score(a)
        flag, action = recommended_action(a, score, subs)
        accounts.append({
            **a,
            "health_score": score,
            "status": status_from_score(score),
            "sub_scores": subs,
            "flag": flag,             # churn | expansion | healthy | watch
            "recommended_action": action,
        })
    accounts.sort(key=lambda x: x["health_score"])  # worst first: triage view
    return accounts


def portfolio_summary(accounts):
    total_arr = sum(a["arr"] for a in accounts)
    at_risk = [a for a in accounts if a["status"] in ("At-Risk", "Critical")]
    return {
        "as_of": AS_OF.isoformat(),
        "total_accounts": len(accounts),
        "total_arr": total_arr,
        "healthy": sum(1 for a in accounts if a["status"] == "Healthy"),
        "at_risk": sum(1 for a in accounts if a["status"] == "At-Risk"),
        "critical": sum(1 for a in accounts if a["status"] == "Critical"),
        "arr_at_risk": sum(a["arr"] for a in at_risk),
        "expansion_opportunities": sum(1 for a in accounts if a["flag"] == "expansion"),
    }


def main():
    accounts = build_portfolio()
    summary = portfolio_summary(accounts)
    payload = {"summary": summary, "accounts": accounts}

    with open("accounts.json", "w") as f:
        json.dump(payload, f, indent=2)

    # Console summary so the logic is legible when you run it.
    print(f"CustomerGuard  |  portfolio as of {summary['as_of']}")
    print("=" * 68)
    print(f"{summary['total_accounts']} accounts  |  "
          f"${summary['total_arr']:,} total ARR  |  "
          f"${summary['arr_at_risk']:,} ARR at risk")
    print(f"Healthy {summary['healthy']}  |  At-Risk {summary['at_risk']}  |  "
          f"Critical {summary['critical']}  |  "
          f"Expansion signals {summary['expansion_opportunities']}")
    print("-" * 68)
    for a in accounts:
        print(f"[{a['health_score']:>3}] {a['status']:<9} {a['name']:<28} "
              f"{a['flag']}")
    print("-" * 68)
    print("Wrote accounts.json")


if __name__ == "__main__":
    main()
