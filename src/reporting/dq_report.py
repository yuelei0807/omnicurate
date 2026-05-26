"""Generate outputs/data_quality_report.md from dq_exception_report."""

from __future__ import annotations

from pathlib import Path

import duckdb

from src.config import settings
from src.validation.rule_registry import REGISTRY, all_rules


def render(con: duckdb.DuckDBPyConnection) -> str:
    """Build markdown report text from dq_exception_report."""
    total = int(
        con.execute("SELECT COUNT(*) AS n FROM dq_exception_report").fetchdf().iloc[0]["n"]
    )
    unique_rules = int(
        con.execute(
            "SELECT COUNT(DISTINCT rule_id) AS n FROM dq_exception_report"
        ).fetchdf().iloc[0]["n"]
    )

    sev_df = con.execute(
        """
        SELECT severity, COUNT(*) AS n
        FROM dq_exception_report
        GROUP BY severity
        ORDER BY severity
        """
    ).fetchdf()

    by_rule_df = con.execute(
        """
        SELECT rule_id, COUNT(*) AS violations
        FROM dq_exception_report
        GROUP BY rule_id
        ORDER BY rule_id
        """
    ).fetchdf()

    lines: list[str] = []
    lines.append("# Data Quality Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total exceptions:** {int(total)}")
    lines.append(f"- **Unique rules triggered:** {int(unique_rules)}")
    lines.append("")
    lines.append("### Severity breakdown")
    lines.append("")
    if len(sev_df) == 0:
        lines.append("_No exceptions recorded._")
    else:
        lines.append("| Severity | Count |")
        lines.append("|----------|------:|")
        for _, row in sev_df.iterrows():
            lines.append(f"| {row['severity']} | {int(row['n'])} |")
    lines.append("")

    lines.append("## By Rule")
    lines.append("")
    if len(by_rule_df) == 0:
        lines.append("_No exceptions recorded._")
    else:
        lines.append("| Rule | Description | Severity | Violations |")
        lines.append("|------|-------------|----------|----------:|")
        for _, row in by_rule_df.iterrows():
            rid = str(row["rule_id"])
            rule = REGISTRY[rid]
            desc = rule.description.replace("|", "\\|")
            lines.append(
                f"| {rid} | {desc} | {rule.severity} | {int(row['violations'])} |"
            )

    lines.append("")
    lines.append("## Sample records")
    lines.append("")
    lines.append("Up to five example rows per rule (most recent first).")
    lines.append("")

    for rule in all_rules():
        rid = rule.rule_id
        sample_df = con.execute(
            """
            SELECT record_key, severity, issue_description
            FROM dq_exception_report
            WHERE rule_id = ?
            ORDER BY detected_at DESC
            LIMIT 5
            """,
            [rid],
        ).fetchdf()

        lines.append(f"### {rid}")
        lines.append("")
        if len(sample_df) == 0:
            lines.append("_No violations for this rule._")
        else:
            lines.append("| Record key | Severity | Issue |")
            lines.append("|------------|----------|-------|")
            for _, srow in sample_df.iterrows():
                issue = str(srow["issue_description"]).replace("|", "\\|")
                if len(issue) > 120:
                    issue = issue[:117] + "..."
                lines.append(
                    f"| {srow['record_key']} | {srow['severity']} | {issue} |"
                )
        lines.append("")

    return "\n".join(lines)


def write(con: duckdb.DuckDBPyConnection) -> Path:
    """Render report and write to settings.DQ_REPORT_MD; return path."""
    settings.ensure_output_dir()
    path = settings.DQ_REPORT_MD
    path.write_text(render(con), encoding="utf-8")
    return path