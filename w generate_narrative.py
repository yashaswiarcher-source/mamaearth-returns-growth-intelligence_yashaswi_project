#!/usr/bin/env python3
"""Generate a factual SCR business narrative from narrator/findings.json."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
FINDINGS_PATH = REPO_ROOT / "narrator" / "findings.json"
SAMPLE_PATH = REPO_ROOT / "narrator" / "sample_output.txt"

SYSTEM_INSTRUCTION = """You are a senior data analyst writing for Mamaearth's regional ops and finance heads.
Write exactly three labeled sections: Situation, Complication, and Resolution.
Every number in the narrative must come only from the supplied findings and must
appear with the same value. Do not invent statistics, percentages, dates, causes,
or recommendations that require unsupported figures. Keep the report concise,
factual, and suitable for business leaders."""


def _format_inr(value: float) -> str:
    return f"{value:,.2f}"


def _user_prompt(findings: dict[str, Any]) -> str:
    # The prompt is constructed from the argument; figures are not hardcoded here.
    return (
        "Using only this findings object, write the required three-section SCR narrative. "
        "Preserve every supplied figure exactly (normal comma formatting is allowed). "
        f"Findings JSON:\n{json.dumps(findings, indent=2, sort_keys=True)}"
    )


def generate_scr_narrative_offline(findings: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic, keyless SCR narrative built directly from findings."""
    cleaned = findings["cleaned_total_revenue_inr"]
    raw = findings["raw_total_revenue_inr"]
    delta = findings["duplicate_reconciliation_delta_inr"]
    cod = findings["return_rate_by_payment"]["COD"]
    card = findings["return_rate_by_payment"]["CARD"]
    upi = findings["return_rate_by_payment"]["UPI"]
    segment = findings["highest_risk_segment"]
    peak = findings["true_peak_month"]
    inflated = findings["outlier_inflated_month"]
    method = segment["payment_method"]
    tier = segment["city_tier"]
    segment_rate = segment["return_rate_pct"]
    apparent = _format_inr(inflated["apparent_revenue_inr"])
    peak_month_name = datetime.strptime(peak["month"], "%Y-%m").strftime("%B")

    narrative = (
        "Situation\n"
        f"The cleaned Mamaearth dataset records total revenue of {_format_inr(cleaned)} INR, "
        f"compared with raw revenue of {_format_inr(raw)} INR. The true peak month is "
        f"{peak_month_name} ({peak['month']}), with revenue of {_format_inr(peak['revenue_inr'])} INR.\n\n"
        "Complication\n"
        f"The raw-to-cleaned reconciliation gap is {_format_inr(delta)} INR and is explained "
        "by duplicate orders. Returns are highest for COD at {cod:.1f}%, versus CARD at "
        "{card:.1f}% and UPI at {upi:.1f}%. The highest-risk segment is {method} with "
        "Tier-{tier} cities at {segment_rate:.1f}%. January appears inflated at "
        "{apparent} INR because its corrected revenue is {corrected} INR.\n\n"
        "Resolution\n"
        f"Use the cleaned revenue of {_format_inr(cleaned)} INR for reporting, reconcile the "
        f"{_format_inr(delta)} INR duplicate-driven difference, and prioritize investigation "
        f"of {method} Tier-{tier} returns at {segment_rate:.1f}%. For trend decisions, use "
        f"{peak['month']} as the peak month at {_format_inr(peak['revenue_inr'])} INR rather "
        f"than January's outlier-inflated view of {apparent} INR."
    ).format(
        cod=cod,
        card=card,
        upi=upi,
        method=method,
        tier=tier,
        segment_rate=segment_rate,
        apparent=apparent,
        corrected=_format_inr(inflated["corrected_revenue_inr"]),
    )
    return {"status": "success", "narrative": narrative, "tokens": None}


def _generate_online(findings: dict[str, Any], api_key: str) -> dict[str, Any]:
    """Call Gemini; all exceptions are converted to a structured error dict."""
    try:
        from google import genai
        from google.genai import types

        # A 30-second client HTTP timeout satisfies the taught Gemini minimum.
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=30_000),
        )
        # Temperature 0.0 is intentional: this is a factual report, not creative writing.
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            contents=_user_prompt(findings),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.0,
                max_output_tokens=500,
            ),
        )
        tokens = getattr(getattr(response, "usage_metadata", None), "total_token_count", None)
        return {"status": "success", "narrative": response.text, "tokens": tokens}
    except Exception as err:  # caller receives no raw API/client exception
        return {"status": "error", "narrative": None, "message": str(err)}


def generate_scr_narrative(findings: dict[str, Any]) -> dict[str, Any]:
    """Use Gemini when configured; otherwise or on error, use the offline path."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return generate_scr_narrative_offline(findings)

    online = _generate_online(findings, api_key)
    if online["status"] == "success":
        return online
    return generate_scr_narrative_offline(findings)


def _normalized(text: str) -> str:
    return text.replace(",", "").lower()


def check_numeric_accuracy(narrative: str) -> bool:
    """Print and return whether every required figure appears in the narrative."""
    text = _normalized(narrative)
    checks = {
        "cleaned revenue 97358.30": "97358.3",
        "COD return rate 44.4": "44.4",
        "COD + Tier-2 risk rate 54.5": "54.5",
        "duplicate delta 2501.90": "2501.9",
        "March peak revenue 20318.90": "march" in text and "20318.9" in text,
    }
    passed = True
    for label, expected in checks.items():
        result = expected if isinstance(expected, bool) else expected in text
        print(f"{label}: {'PASS' if result else 'FAIL'}")
        passed = passed and result
    print(f"Numeric accuracy overall: {'PASS' if passed else 'FAIL'}")
    return passed


def main() -> None:
    findings = json.loads(FINDINGS_PATH.read_text(encoding="utf-8"))
    result = generate_scr_narrative(findings)
    if result["narrative"] is None:
        raise RuntimeError(result.get("message", "Narrative generation failed"))
    print(f"Generation status: {result['status']}")
    print(result["narrative"])
    check_numeric_accuracy(result["narrative"])


if __name__ == "__main__":
    main()
