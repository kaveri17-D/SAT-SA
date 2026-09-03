"""HTML Report Exporter."""
import html as html_escape
from app.models import ReportSnapshot


class HTMLReportExporter:
    """Exports report snapshot into polished, standalone HTML document across all 5 report categories."""

    @staticmethod
    def export(snapshot: ReportSnapshot) -> str:
        s = snapshot.summary_json or {}
        c = snapshot.content_json or {}
        rep_type = snapshot.report_type.value if hasattr(snapshot.report_type, "value") else str(snapshot.report_type)

        # Defensive datetime formatting
        gen_at = snapshot.generated_at
        if hasattr(gen_at, 'strftime'):
            gen_str = gen_at.strftime('%Y-%m-%d %H:%M:%S UTC')
        else:
            gen_str = str(gen_at or 'RECENT')

        # Primary metrics computation
        score = s.get('overall_risk_score', s.get('score', 0.0))
        total_findings = s.get('total_findings', s.get('findings_count', 0))
        critical_findings = s.get('critical_findings', 0)
        kev_count = s.get('kev_exposures_count', s.get('cisa_kev_cves', s.get('kev_exposed_assets', 0)))

        # Polymorphic Category Content
        category_sections = ""

        if rep_type == "TECHNICAL":
            findings_list = c.get("detailed_findings", [])
            rows = ""
            for f in findings_list[:30]:
                fid = html_escape.escape(str(f.get("finding_id", "")))[:16]
                rid = html_escape.escape(str(f.get("rule_id", "")))
                sev = html_escape.escape(str(f.get("severity", "MEDIUM")))
                reason = html_escape.escape(str(f.get("reason", "")))
                rec = html_escape.escape(str(f.get("recommendation", "")))
                sev_color = "#f87171" if sev == "CRITICAL" else ("#fb923c" if sev == "HIGH" else "#38bdf8")
                rows += f"""
                <tr>
                  <td style="font-family: monospace; color: #94a3b8;">{fid}...</td>
                  <td style="font-weight: 600;">{rid}</td>
                  <td><span style="color: {sev_color}; font-weight: 700;">{sev}</span></td>
                  <td style="color: #cbd5e1;">{reason}</td>
                  <td style="color: #38bdf8;">{rec}</td>
                </tr>
                """
            category_sections = f"""
            <div class="section">
              <div class="section-title">TECHNICAL FINDINGS & ROOT CAUSES ({len(findings_list)} Identified)</div>
              <table class="table">
                <thead>
                  <tr>
                    <th>Finding ID</th>
                    <th>Rule ID</th>
                    <th>Severity</th>
                    <th>Observed Deviation / Reason</th>
                    <th>Supervisory Action</th>
                  </tr>
                </thead>
                <tbody>{rows}</tbody>
              </table>
            </div>
            """

        elif rep_type == "RISK":
            decomp = c.get("risk_decomposition", {})
            rows = ""
            for comp, val in decomp.items():
                c_name = html_escape.escape(str(comp).replace("_", " ").title())
                c_val = html_escape.escape(str(val))
                rows += f"""
                <tr>
                  <td style="font-weight: 600;">{c_name}</td>
                  <td style="color: #38bdf8; font-weight: 700; text-align: right;">{c_val}</td>
                </tr>
                """
            category_sections = f"""
            <div class="section">
              <div class="section-title">SUPERVISORY RISK DECOMPOSITION</div>
              <p style="color: #94a3b8; font-size: 12px; margin-bottom: 12px;">
                Calculated via 5-Component Normalized Metric Framework: EG (30%) + NS (25%) + PD (20%) + IA (15%) + AC (10%).
              </p>
              <table class="table" style="max-width: 600px;">
                <thead>
                  <tr>
                    <th>Risk Dimension</th>
                    <th style="text-align: right;">Calculated Weight / Value</th>
                  </tr>
                </thead>
                <tbody>{rows}</tbody>
              </table>
            </div>
            """

        elif rep_type == "ASSET":
            profiles = c.get("asset_profiles", [])
            rows = ""
            for a in profiles[:25]:
                aname = html_escape.escape(str(a.get("name", "")))
                atype = html_escape.escape(str(a.get("asset_type", "")))
                crit = html_escape.escape(str(a.get("criticality", "")))
                fcnt = a.get("findings_count", 0)
                vctx = a.get("vulnerability_context", {})
                cve = html_escape.escape(str(vctx.get("cve_id") or "NOMINAL"))
                rows += f"""
                <tr>
                  <td style="font-weight: 600;">{aname}</td>
                  <td style="color: #94a3b8;">{atype}</td>
                  <td><span style="color: {'#f87171' if crit == 'CRITICAL' else '#cbd5e1'}; font-weight: 700;">{crit}</span></td>
                  <td>{fcnt}</td>
                  <td style="font-family: monospace; color: {'#fb923c' if cve != 'NOMINAL' else '#34d399'};">{cve}</td>
                </tr>
                """
            category_sections = f"""
            <div class="section">
              <div class="section-title">ASSET-CENTRIC SECURITY & EXPOSURE PROFILES ({len(profiles)} Assets)</div>
              <table class="table">
                <thead>
                  <tr>
                    <th>Asset Name</th>
                    <th>Type</th>
                    <th>Criticality</th>
                    <th>Findings</th>
                    <th>CVE Reference</th>
                  </tr>
                </thead>
                <tbody>{rows}</tbody>
              </table>
            </div>
            """

        elif rep_type == "VULNERABILITY_THREAT_INTEL":
            cves = c.get("cve_inventory", {})
            rows = ""
            for cve_id, data in list(cves.items())[:20]:
                cid = html_escape.escape(str(cve_id))
                cvss = data.get("cvss_base_score", "—")
                is_kev = data.get("is_cisa_kev", False)
                groups = ", ".join(data.get("threat_groups", [])) or "General Exploitation"
                rows += f"""
                <tr>
                  <td style="font-family: monospace; font-weight: 700; color: #fb923c;">{cid}</td>
                  <td style="color: #38bdf8; font-weight: 700;">{cvss}</td>
                  <td><span style="color: {'#f87171' if is_kev else '#94a3b8'}; font-weight: 700;">{'YES (CISA KEV)' if is_kev else 'NO'}</span></td>
                  <td style="color: #cbd5e1;">{html_escape.escape(groups)}</td>
                </tr>
                """
            category_sections = f"""
            <div class="section">
              <div class="section-title">THREAT INTELLIGENCE & CVE EXPOSURE INVENTORY</div>
              <table class="table">
                <thead>
                  <tr>
                    <th>CVE Identifier</th>
                    <th>CVSS Base</th>
                    <th>CISA KEV Catalog</th>
                    <th>Associated Threat Actors</th>
                  </tr>
                </thead>
                <tbody>{rows}</tbody>
              </table>
            </div>
            """

        else:
            # Executive Summary (Default)
            exec_sum = c.get("executive_summary")
            narrative = exec_sum.get("narrative") if isinstance(exec_sum, dict) else str(exec_sum or "Supervisory assessment completed with verified findings across critical infrastructure assets.")
            gaps = c.get("top_security_gaps", [])
            gap_rows = ""
            for g in gaps:
                rid = html_escape.escape(str(g.get("rule_id", "")))
                sev = html_escape.escape(str(g.get("severity", "HIGH")))
                reason = html_escape.escape(str(g.get("reason", "")))
                rec = html_escape.escape(str(g.get("recommendation", "")))
                gap_rows += f"""
                <tr>
                  <td style="font-weight: 600;">{rid}</td>
                  <td><span style="color: {'#f87171' if sev == 'CRITICAL' else '#fb923c'}; font-weight: 700;">{sev}</span></td>
                  <td style="color: #cbd5e1;">{reason}</td>
                  <td style="color: #38bdf8;">{rec}</td>
                </tr>
                """
            category_sections = f"""
            <div class="section">
              <div class="section-title">EXECUTIVE NARRATIVE</div>
              <p style="line-height: 1.6; color: #cbd5e1; font-size: 13px;">
                {html_escape.escape(narrative)}
              </p>
            </div>
            <div class="section">
              <div class="section-title">TOP SUPERVISORY SECURITY GAPS</div>
              <table class="table">
                <thead>
                  <tr>
                    <th>Rule ID</th>
                    <th>Severity</th>
                    <th>Observed Vulnerability</th>
                    <th>Mandatory Recommendation</th>
                  </tr>
                </thead>
                <tbody>{gap_rows}</tbody>
              </table>
            </div>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html_escape.escape(snapshot.title or "SAT-SA Official Supervisory Report")}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #070a12; color: #f1f5f9; padding: 40px; margin: 0; }}
  .container {{ max-width: 1100px; margin: 0 auto; background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 32px; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); }}
  .header {{ border-bottom: 1px solid #1e293b; padding-bottom: 20px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; }}
  .title {{ font-size: 22px; font-weight: 700; color: #38bdf8; margin: 0 0 8px 0; }}
  .badge {{ display: inline-block; padding: 4px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700; text-transform: uppercase; font-family: monospace; }}
  .badge-critical {{ background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #ef4444; }}
  .badge-verified {{ background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #10b981; }}
  .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px; }}
  .card {{ background: #1e293b; padding: 16px; border-radius: 8px; border: 1px solid #334155; }}
  .card-label {{ font-size: 11px; font-family: monospace; color: #94a3b8; text-transform: uppercase; margin-bottom: 4px; }}
  .card-value {{ font-size: 22px; font-weight: 700; color: #f8fafc; }}
  .section {{ margin-bottom: 32px; }}
  .section-title {{ font-size: 15px; font-weight: 700; color: #38bdf8; border-bottom: 1px solid #334155; padding-bottom: 8px; margin-bottom: 16px; font-family: monospace; }}
  .table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  .table th {{ text-align: left; padding: 10px; background: #1e293b; color: #94a3b8; font-family: monospace; font-size: 11px; text-transform: uppercase; border-bottom: 1px solid #334155; }}
  .table td {{ padding: 10px; border-bottom: 1px solid #1e293b; }}
  .footer {{ margin-top: 40px; padding-top: 16px; border-top: 1px solid #1e293b; font-size: 11px; font-family: monospace; color: #64748b; display: flex; justify-content: space-between; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <div class="badge badge-verified">OFFICIAL SUPERVISORY ASSESSMENT REPORT</div>
      <h1 class="title" style="margin-top: 8px;">{html_escape.escape(snapshot.title or "Supervisory Report")}</h1>
      <div style="font-family: monospace; font-size: 12px; color: #94a3b8;">
        Report No: <span style="color: #38bdf8;">{snapshot.report_number}</span> | Generated: {gen_str} | Scope: {snapshot.report_type.value if hasattr(snapshot.report_type, 'value') else snapshot.report_type}
      </div>
    </div>
    <div style="text-align: right;">
      <div class="badge badge-critical">{s.get('overall_security_posture', 'VALIDATED')}</div>
      <div style="font-family: monospace; font-size: 11px; color: #94a3b8; margin-top: 4px;">Examiner: {snapshot.generated_by}</div>
    </div>
  </div>

  <div class="grid">
    <div class="card">
      <div class="card-label">Risk Score</div>
      <div class="card-value" style="color: #f87171;">{score}<span style="font-size: 12px; color: #94a3b8;">/100</span></div>
    </div>
    <div class="card">
      <div class="card-label">Total Findings</div>
      <div class="card-value">{total_findings}</div>
    </div>
    <div class="card">
      <div class="card-label">Critical Findings</div>
      <div class="card-value" style="color: #f87171;">{critical_findings}</div>
    </div>
    <div class="card">
      <div class="card-label">KEV Exposures</div>
      <div class="card-value" style="color: #fb923c;">{kev_count}</div>
    </div>
  </div>

  {category_sections}

  <div class="footer">
    <div>SHA-256 Checksum: {snapshot.sha256_checksum}</div>
    <div>SAT-SA v1.0.0 | Air-Gap Protocol: STRICT_LOCAL_ONLY</div>
  </div>
</div>
</body>
</html>
"""
