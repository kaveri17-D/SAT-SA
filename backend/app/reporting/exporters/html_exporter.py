"""HTML Report Exporter."""
from app.models import ReportSnapshot


class HTMLReportExporter:
    """Exports report snapshot into polished, standalone HTML document."""

    @staticmethod
    def export(snapshot: ReportSnapshot) -> str:
        s = snapshot.summary_json or {}
        c = snapshot.content_json or {}
        header = c.get("report_header", {})

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{snapshot.title}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #070a12; color: #f1f5f9; padding: 40px; margin: 0; }}
  .container {{ max-width: 1000px; margin: 0 auto; background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 32px; }}
  .header {{ border-bottom: 1px solid #1e293b; padding-bottom: 20px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; }}
  .title {{ font-size: 24px; font-weight: 700; color: #38bdf8; margin: 0 0 8px 0; }}
  .badge {{ display: inline-block; padding: 4px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700; text-transform: uppercase; font-family: monospace; }}
  .badge-critical {{ background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #ef4444; }}
  .badge-high {{ background: rgba(249, 115, 22, 0.2); color: #fb923c; border: 1px solid #f97316; }}
  .badge-verified {{ background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #10b981; }}
  .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px; }}
  .card {{ background: #1e293b; padding: 16px; border-radius: 8px; border: 1px solid #334155; }}
  .card-label {{ font-size: 11px; font-family: monospace; color: #94a3b8; text-transform: uppercase; margin-bottom: 4px; }}
  .card-value {{ font-size: 22px; font-weight: 700; color: #f8fafc; }}
  .section {{ margin-bottom: 32px; }}
  .section-title {{ font-size: 16px; font-weight: 700; color: #38bdf8; border-bottom: 1px solid #334155; padding-bottom: 8px; margin-bottom: 16px; font-family: monospace; }}
  .table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  .table th {{ text-align: left; padding: 10px; background: #1e293b; color: #94a3b8; font-family: monospace; font-size: 11px; text-transform: uppercase; border-bottom: 1px solid #334155; }}
  .table td {{ padding: 10px; border-bottom: 1px solid #1e293b; }}
  .footer {{ margin-top: 40px; padding-top: 16px; border-top: 1px solid #1e293b; font-size: 11px; font-family: monospace; color: #64748b; display: flex; justify-content: space-between; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <div class="badge badge-verified">OFFICIAL SUPERVISORY REPORT</div>
      <h1 class="title" style="margin-top: 8px;">{snapshot.title}</h1>
      <div style="font-family: monospace; font-size: 12px; color: #94a3b8;">
        Report No: <span style="color: #38bdf8;">{snapshot.report_number}</span> | Generated: {snapshot.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
      </div>
    </div>
    <div style="text-align: right;">
      <div class="badge badge-critical">{s.get('overall_security_posture', 'ACTIVE')}</div>
      <div style="font-family: monospace; font-size: 11px; color: #94a3b8; margin-top: 4px;">Examiner: {snapshot.generated_by}</div>
    </div>
  </div>

  <div class="grid">
    <div class="card">
      <div class="card-label">Risk Score</div>
      <div class="card-value" style="color: #f87171;">{s.get('overall_risk_score', 0.0)}<span style="font-size: 12px; color: #94a3b8;">/100</span></div>
    </div>
    <div class="card">
      <div class="card-label">Total Findings</div>
      <div class="card-value">{s.get('total_findings', 0)}</div>
    </div>
    <div class="card">
      <div class="card-label">Critical Findings</div>
      <div class="card-value" style="color: #f87171;">{s.get('critical_findings', 0)}</div>
    </div>
    <div class="card">
      <div class="card-label">KEV Exposures</div>
      <div class="card-value" style="color: #fb923c;">{s.get('kev_exposures_count', 0)}</div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">EXECUTIVE NARRATIVE</div>
    <p style="line-height: 1.6; color: #cbd5e1;">
      {c.get('executive_summary', {}).get('narrative', 'Supervisory assessment completed with verified findings.')}
    </p>
  </div>

  <div class="footer">
    <div>SHA-256 Checksum: {snapshot.sha256_checksum}</div>
    <div>SAT-SA v1.0.0 | Air-Gap Mode: STRICT_LOCAL_ONLY</div>
  </div>
</div>
</body>
</html>
"""
        return html
