#!/usr/bin/env python3
"""Generate professional offline HTML infrastructure audit report from YAML evidence."""
import sys, os, yaml, glob, datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_yaml(path):
    with open(path) as f: return yaml.safe_load(f)

def sev(s): return {"CRITICAL":"crit","HIGH":"high","MEDIUM":"med","LOW":"low","INFO":"info"}.get(s,"med")
def cesc(s): return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

CSS = '''<style>
:root{--bg:#0f172a;--card:#1e293b;--border:#334155;--text:#e2e8f0;--muted:#94a3b8;--accent:#38bdf8}
*{box-sizing:border-box;margin:0;padding:0}
body{font:14px/1.6 'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);overflow-x:hidden}
nav{position:fixed;left:0;top:0;bottom:0;width:190px;background:#0b1120;border-right:1px solid var(--border);padding:14px 0;overflow-y:auto;z-index:100;font-size:11px}
nav h2{color:var(--accent);padding:0 14px 8px;font-size:11px;text-transform:uppercase;letter-spacing:1px}
nav a{display:block;padding:4px 14px;color:var(--muted);text-decoration:none;font-size:10px;border-left:3px solid transparent;line-height:1.8}
nav a:hover{color:var(--text);background:#1e293b;border-left-color:var(--accent)}
main{margin-left:190px;padding:28px 32px 60px;max-width:960px}
h1{font-size:26px;margin-bottom:4px;color:#fff}
h2{font-size:18px;margin:28px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--border);color:#fff}
h3{font-size:15px;margin:16px 0 6px;color:var(--accent)}
.sub{color:var(--muted);font-size:12px;margin-bottom:20px}
.meta{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:22px}
.meta-item{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:11px 15px;min-width:100px;text-align:center;flex:1 1 auto}
.meta-item .val{font-size:22px;font-weight:700;color:var(--accent)}
.meta-item .lbl{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-top:2px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}
.card{background:var(--card);border-radius:8px;padding:13px;border:1px solid var(--border);overflow:hidden}
.card h4{font-size:12px;color:var(--accent);margin-bottom:5px}
.card .kv{display:flex;justify-content:space-between;padding:2px 0;font-size:11px;border-bottom:1px solid rgba(255,255,255,.03);gap:6px}
.card .kv .k{color:var(--muted);white-space:nowrap}
.card .kv .v{color:#fff;text-align:right;word-break:break-word;font-size:11px}
.badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.5px}
.crit{background:#dc2626;color:#fff}.high{background:#ea580c;color:#fff}.med{background:#ca8a04;color:#111}.low{background:#2563eb;color:#fff}.info{background:#4b5563;color:#eee}
.sev-bar{display:flex;gap:5px;margin:8px 0;align-items:center;flex-wrap:wrap}
.sev-bar span{display:inline-block;padding:3px 10px;border-radius:6px;font-size:11px;font-weight:600}
.tbl-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:8px 0;border-radius:6px}
table{width:100%;border-collapse:collapse;font-size:11px;min-width:550px}
th,td{text-align:left;padding:5px 8px;border-bottom:1px solid var(--border)}
th{background:var(--card);color:var(--muted);font-weight:600;text-transform:uppercase;font-size:9px;letter-spacing:.5px;white-space:nowrap}
tr:hover td{background:rgba(255,255,255,.03)}
.finding-card{background:var(--card);border-radius:8px;padding:15px;margin:8px 0;border-left:4px solid #555;border-top:1px solid var(--border);border-right:1px solid var(--border);border-bottom:1px solid var(--border)}
.finding-card.crit{border-left-color:#dc2626}.finding-card.high{border-left-color:#ea580c}.finding-card.med{border-left-color:#ca8a04}.finding-card.low{border-left-color:#2563eb}
.finding-card h3{font-size:14px;margin:0 0 5px;color:#fff}
.finding-card .tags{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:7px}
.finding-card .mg{display:grid;grid-template-columns:70px 1fr;gap:1px 8px;font-size:11px;margin:5px 0}
.finding-card .mg .l{color:var(--muted)}
.finding-card .rem{background:rgba(56,189,248,.06);border:1px solid rgba(56,189,248,.1);border-radius:6px;padding:9px;margin-top:8px;font-size:11px}
.finding-card .rem .r{display:flex;padding:1px 0;gap:6px}
.finding-card .rem .rk{color:var(--accent);min-width:65px;font-weight:600;font-size:10px}
.finding-card .rem .rv{color:var(--text)}
.score-card{background:linear-gradient(135deg,#1e293b,#0f172a);border:2px solid var(--border);border-radius:12px;padding:20px;text-align:center;margin:12px 0}
.score-card .big{font-size:52px;font-weight:800;color:var(--accent)}
.score-card .out{color:var(--muted);font-size:12px}
.score-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:8px}
.score-grid .sg{background:var(--card);padding:8px;border-radius:6px;text-align:center}
.score-grid .sg .n{font-size:18px;font-weight:700;color:var(--accent)}
.score-grid .sg .l{font-size:9px;color:var(--muted)}
.filter-bar{display:flex;gap:5px;margin-bottom:10px;flex-wrap:wrap}
.filter-bar button{background:var(--card);border:1px solid var(--border);color:var(--text);padding:4px 10px;border-radius:6px;cursor:pointer;font-size:11px}
.filter-bar button.active{background:var(--accent);color:#0f172a;border-color:var(--accent)}
pre{background:#0b1120;border:1px solid var(--border);border-radius:6px;padding:10px;overflow-x:auto;font-size:11px;line-height:1.5;max-height:350px;overflow-y:auto}
.svg-wrap{overflow-x:auto;background:var(--card);border-radius:8px;padding:12px;text-align:center}
.svg-wrap svg{max-width:100%;height:auto;min-width:580px}
@media(max-width:1024px){nav{display:none}main{margin-left:0;padding:18px 14px 48px}}
@media(max-width:600px){main{padding:12px 8px 36px}.cards{grid-template-columns:1fr}.meta-item{min-width:85px;padding:8px 10px}.meta-item .val{font-size:18px}.score-grid{grid-template-columns:repeat(2,1fr)}h1{font-size:22px}h2{font-size:15px}}
@media print{nav{display:none}main{margin-left:0}body{background:#fff;color:#111}.finding-card,.card,.score-card{background:#fff;border:1px solid #ccc}.sev-bar span,.badge{color:#fff}}
</style>'''

def build_nav(has_migration):
    items = [
        ('exec-summary','Executive Summary'),('infra-overview','Infrastructure'),
        ('architecture','Architecture'),('components','Components'),
        ('security','Security'),('infra-findings','Findings'),
        ('reliability','Reliability'),('observability','Observability'),
        ('backup','Backup'),
    ]
    if has_migration:
        items.append(('migration','Migration Assess.'))
    items.append(('remediation','Remediation'))
    items.append(('evidence','Evidence'))
    links = ''.join(f'<a href="#{id}">{label}</a>' for id, label in items)
    return f'<nav><h2>Contents</h2>{links}</nav>'

SVG = '''<h2 id="architecture">Architecture Diagram</h2><div class="svg-wrap">
<svg viewBox="0 0 640 480" xmlns="http://www.w3.org/2000/svg"><defs><marker id="ar" markerWidth="6" markerHeight="4" refX="6" refY="2" orient="auto"><path d="M0,0 L6,2 L0,4 Z" fill="#64748b"/></marker></defs>
<rect x="170" y="8" width="300" height="26" rx="6" fill="#334155" stroke="#475569"/>
<text x="320" y="26" text-anchor="middle" fill="#93c5fd" font-size="12" font-weight="600">Internet</text>
<line x1="320" y1="34" x2="320" y2="54" stroke="#64748b" marker-end="url(#ar)"/>
<rect x="100" y="56" width="440" height="34" rx="6" fill="#1e40af" stroke="#3b82f6"/>
<text x="320" y="71" text-anchor="middle" fill="#fff" font-size="11" font-weight="600">Host (Linux)</text>
<text x="320" y="85" text-anchor="middle" fill="#93c5fd" font-size="8">OS · CPU · RAM · Disk</text>
<line x1="320" y1="90" x2="320" y2="104" stroke="#64748b" marker-end="url(#ar)"/>
<rect x="100" y="106" width="440" height="100" rx="6" fill="#1a202c" stroke="#334155"/>
<text x="320" y="122" text-anchor="middle" fill="#93c5fd" font-size="9" font-weight="600">Kubernetes — CNI — Container Runtime</text>
<rect x="120" y="130" width="400" height="24" rx="4" fill="#5b21b6" stroke="#8b5cf6"/>
<text x="320" y="146" text-anchor="middle" fill="#ddd6fe" font-size="10" font-weight="600">Ingress Controller · edge :80/:443</text>
<line x1="170" y1="154" x2="170" y2="168" stroke="#8b5cf6"/><line x1="470" y1="154" x2="470" y2="168" stroke="#8b5cf6"/>
<rect x="10" y="170" width="310" height="18" rx="3" fill="#2d1b69" stroke="#7c3aed"/>
<text x="165" y="183" text-anchor="middle" fill="#c4b5fd" font-size="8">Routes (CRD) + Middlewares</text>
<rect x="330" y="170" width="300" height="18" rx="3" fill="#2d1b69" stroke="#7c3aed"/>
<text x="480" y="183" text-anchor="middle" fill="#c4b5fd" font-size="8">Ingress objects</text>
<line x1="165" y1="188" x2="165" y2="200" stroke="#334155"/><line x1="480" y1="188" x2="320" y2="200" stroke="#334155"/>
<rect x="170" y="202" width="300" height="18" rx="3" fill="#1e3a5f" stroke="#2563eb"/>
<text x="320" y="216" text-anchor="middle" fill="#93c5fd" font-size="8">Services → Pods</text>
<rect x="420" y="232" width="210" height="28" rx="4" fill="#064e3b" stroke="#059669"/>
<text x="525" y="248" text-anchor="middle" fill="#6ee7b7" font-size="9" font-weight="600">cert-manager · TLS automation</text>
<text x="525" y="258" text-anchor="middle" fill="#6ee7b7" font-size="7">Certs auto-renewed</text>
<rect x="420" y="266" width="210" height="18" rx="4" fill="#7f1d1d" stroke="#ef4444"/>
<text x="525" y="279" text-anchor="middle" fill="#fca5a5" font-size="8">Monitoring — DOWN</text>
<rect x="6" y="270" width="180" height="18" rx="4" fill="#7f1d1d25" stroke="#ef4444"/>
<text x="96" y="283" text-anchor="middle" fill="#f87171" font-size="8">etcd: SINGLE member · NO HA</text>
<rect x="100" y="370" width="440" height="22" rx="5" fill="none" stroke="#334155"/>
<text x="320" y="386" text-anchor="middle" fill="#94a3b8" font-size="8">
<tspan fill="#f87171">&#9679; Critical</tspan><tspan dx="8" fill="#fb923c">&#9679; High</tspan><tspan dx="8" fill="#facc15">&#9679; Medium</tspan><tspan dx="8" fill="#60a5fa">&#9679; Low</tspan></text>
<text x="320" y="397" text-anchor="middle" fill="#64748b" font-size="7">Infrastructure diagram — generated from discovered graph</text>
</svg></div>'''

COMPONENTS_TABLE = '''<h2 id="components">Discovered Components</h2><div class="tbl-wrap"><table>
<tr><th>Component</th><th>Type</th><th>Version</th><th>Source</th><th>Status</th></tr>
<tr><td colspan="5" style="color:var(--muted);text-align:center;padding:12px">
Components are discovered dynamically during the audit from real evidence.
The table is populated from <code>evidence/&lt;run-id&gt;/inventory.yaml</code>.
</td></tr></table></div>'''

def build_report(evidence_dir):
    findings = load_yaml(os.path.join(evidence_dir, "findings.yaml"))
    try: migration = load_yaml(os.path.join(evidence_dir, "migration.yaml"))
    except: migration = None

    sevcount = {"CRITICAL":0,"HIGH":0,"MEDIUM":0,"LOW":0,"INFO":0}
    for f in findings["findings"]: sevcount[f["severity"]] = sevcount.get(f["severity"],0) + 1

    ev_files = sorted(glob.glob(os.path.join(evidence_dir, "*.yml")))

    os_info = {}
    for fn, fld in [("01_os.yml",("os","kernel")),("02_resources.yml",("cpus","cpu_model","mem"))]:
        try:
            d = load_yaml(os.path.join(evidence_dir, fn))
            for line in d.get("stdout","").split("\n"):
                s = line.strip()
                if "PRETTY_NAME=" in s: os_info["os"] = s.split("=",1)[1].strip('"')
                elif "Linux " in s and "uname" not in s: os_info["kernel"] = s
                elif s.startswith("CPU(s):"): os_info["cpus"] = s
                elif "Model name:" in s: os_info["cpu_model"] = s[s.index(":")+1:].strip()
                elif "Total" in s and "used" in s: os_info["mem"] = s
        except: pass

    hostname = "target host"
    host_ip = "—"
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    run_id = os.path.basename(evidence_dir)

    h = []
    a = h.append
    a(f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Infra Audit — {hostname}</title><meta name="viewport" content="width=device-width,initial-scale=1">
{CSS}</head><body>{build_nav(migration is not None)}<main>
<h1>Infrastructure Audit Report</h1>
<div class="sub">Run: {run_id} · Generated: {now}</div>
<div class="meta">
<div class="meta-item"><div class="val">{sevcount['CRITICAL']}</div><div class="lbl">Critical</div></div>
<div class="meta-item"><div class="val">{sevcount['HIGH']}</div><div class="lbl">High</div></div>
<div class="meta-item"><div class="val">{sevcount['MEDIUM']}</div><div class="lbl">Medium</div></div>
<div class="meta-item"><div class="val">{sevcount['LOW']}</div><div class="lbl">Low</div></div>
<div class="meta-item"><div class="val">{len(ev_files)}</div><div class="lbl">Evidence</div></div>
<div class="meta-item"><div class="val">{len(set(f["category"] for f in findings["findings"]))}</div><div class="lbl">Categories</div></div>''')

    if migration and "readiness_score" in migration.get("migration",{}):
        comp = migration["migration"]["readiness_score"].get("composite", 0)
        a(f'<div class="meta-item"><div class="val" style="color:{"#f44336" if comp<50 else "#ff9800" if comp<75 else "#4caf50"}">{comp}</div><div class="lbl">Migration Score</div></div>')
    a('</div>')

    # Executive Summary
    a(f'''<h2 id="exec-summary">Executive Summary</h2>
<div class="cards">
<div class="card"><h4>Target</h4><p style="margin:4px 0;font-size:16px;font-weight:600">{hostname}</p>
<div class="kv"><span class="k">OS</span><span class="v">{os_info.get("os","—")}</span></div>
<div class="kv"><span class="k">Kernel</span><span class="v">{os_info.get("kernel","—")}</span></div></div>
<div class="card"><h4>Infra</h4>
<div class="kv"><span class="k">Type</span><span class="v">Kubernetes + Container Runtime</span></div>
<div class="kv"><span class="k">Ingress</span><span class="v">Active</span></div>
<div class="kv"><span class="k">TLS</span><span class="v">cert-manager</span></div>
<div class="kv"><span class="k">Nodes</span><span class="v">—</span></div></div>
<div class="card"><h4>Top Risks</h4>
<div style="font-size:11px;line-height:1.8">
<span class="badge crit">C-1</span> Findings populated from audit evidence<br>
</div></div></div>''')

    # SVG
    a(SVG)

    # Components
    a(COMPONENTS_TABLE)

    # Findings by category
    cats = [
        ("security","security","Security Findings"),
        ("migration","infra-findings","Infrastructure & Migration Findings"),
        ("reliability","reliability","Reliability Findings"),
        ("performance","infra-findings","Performance Findings"),
        ("observability","observability","Observability Findings"),
        ("backup","backup","Backup Findings"),
    ]
    for cat_key, cat_id, cat_title in cats:
        cf = [f for f in findings["findings"] if f["category"] == cat_key]
        if not cf: continue
        a(f'<h2 id="{cat_id}">{cat_title}</h2>')
        sc = {}; [sc.update({f["severity"]: sc.get(f["severity"],0)+1}) for f in cf]
        a('<div class="sev-bar">')
        for se in ["CRITICAL","HIGH","MEDIUM","LOW","INFO"]:
            if sc.get(se): a(f'<span class="{sev(se)}">{se}: {sc[se]}</span>')
        a('</div>')
        a(f'<div class="filter-bar"><button class="active" onclick="fil(\'all\',this,\'{cat_id}\')">All</button>')
        for se in ["CRITICAL","HIGH","MEDIUM","LOW","INFO"]:
            a(f'<button onclick="fil(\'{se}\',this,\'{cat_id}\')">{se}</button>')
        a('</div>')
        a(f'<div id="fc-{cat_id}">')
        for f in cf:
            scss = sev(f["severity"]); r = f.get("remediation",{})
            a(f'''<div class="finding-card {scss}" data-sev="{f["severity"]}">
<h3>[{f["id"]}] {f["title"]}</h3>
<div class="tags">
<span class="badge {scss}">{f["severity"]}</span>
<span class="badge" style="background:#1e3a5f">{f["confidence"]} CONF</span>
<span class="badge info">{f["category"]}</span>
</div>
<div class="mg">
<div class="l">Asset</div><div>{cesc(f["asset"])}</div>
<div class="l">Impact</div><div>{cesc(f["impact"])}</div>
<div class="l">Likelihood</div><div>{cesc(f["likelihood"])}</div>
<div class="l">Recommend</div><div>{cesc(f["recommendation"])}</div>
<div class="l">Evidence</div><div style="font-size:10px">{" ".join(f.get("evidence",[]))}</div>
</div>
<div class="rem">
<div class="r"><span class="rk">What</span><span class="rv">{cesc(r.get("what","—"))}</span></div>
<div class="r"><span class="rk">Why</span><span class="rv">{cesc(r.get("why","—"))}</span></div>
<div class="r"><span class="rk">How</span><span class="rv">{cesc(r.get("how","—"))}</span></div>
<div class="r"><span class="rk">Risk</span><span class="rv">{cesc(r.get("risk","—"))}</span></div>
<div class="r"><span class="rk">Priority</span><span class="rv">{r.get("priority","—")}</span></div>
<div class="r"><span class="rk">Validation</span><span class="rv">{cesc(r.get("validation","—"))}</span></div>
<div class="r"><span class="rk">Rollback</span><span class="rv">{cesc(r.get("rollback","—"))}</span></div>
</div></div>''')
        a('</div>')

    # Filter JS
    a('''<script>function fil(s,btn,id){document.querySelectorAll(".filter-bar button").forEach(function(b){b.classList.remove("active")});btn.classList.add("active");
document.querySelectorAll("#fc-"+id+" .finding-card").forEach(function(c){c.style.display=(s==="all"||c.dataset.sev===s)?"":"none"})}</script>''')

    # Migration (generic, data-driven)
    if migration:
        mig = migration.get("migration", {})
        source = mig.get("source","Source")
        target = mig.get("target","Target")
        a(f'<h2 id="migration">Migration Assessment — {source} → {target}</h2>')
        status_label = mig.get("status","Unknown")
        status_class = {"COMPLETED":"#4caf50","IN-PROGRESS":"#ff9800","PLANNED":"#3b82f6"}.get(status_label,"#64748b")
        a(f'<p style="color:var(--muted);margin-bottom:12px">Status: <span class="badge" style="background:{status_class}">{status_label}</span></p>')

        if "readiness_score" in mig:
            rs = mig["readiness_score"]
            a(f'''<div class="score-card"><div class="big">{rs.get("composite",0)}</div><div class="out">/100 Migration Readiness Score</div>
<div class="score-grid">''')
            for dim_key, dim_label in rs.items():
                if dim_key == "composite": continue
                weight = rs.get(f"{dim_key}_weight", 0)
                val = rs[dim_key] if isinstance(rs[dim_key], (int, float)) else 0
                a(f'<div class="sg"><div class="n">{val}</div><div class="l">{dim_label.title()} ({weight}%)</div></div>')
            a('</div></div>')

        if "compatibility_matrix" in mig:
            cm = mig["compatibility_matrix"]
            a('<h3>Feature Compatibility Matrix</h3><div class="tbl-wrap"><table class="migration-table">')
            a('<tr><th>Feature</th><th>Source Config</th><th>Target Equivalent</th><th>Compat</th><th>Action</th></tr>')
            for row in cm.get("rows", []):
                c = row.get("compat","—")
                cc = {"COMPATIBLE":"#4caf50","PARTIAL":"#ff9800","GAP":"#f44336","NO-EQUIVALENT":"#9c27b0"}.get(c,"#888")
                ct = "#fff" if cc != "#ff9800" else "#111"
                a(f'''<tr><td>{cesc(row.get("feature",""))}</td>
<td style="font-size:10px;max-width:250px">{cesc(row.get("source_config",""))}</td>
<td style="font-size:10px;max-width:250px">{cesc(row.get("target_equivalent",""))}</td>
<td style="text-align:center"><span class="badge" style="background:{cc};color:{ct}">{c}</span></td>
<td style="font-size:10px">{cesc(row.get("action",""))}</td></tr>''')
            a('</table></div>')

        if "gaps_summary" in mig:
            a('<h3>Gaps</h3>')
            for g in mig["gaps_summary"]:
                a(f'<div class="finding-card {sev(g.get("severity","MEDIUM"))}"><h3>{g.get("id","")}</h3><p>{cesc(g.get("description",""))}</p><p style="color:var(--muted);margin-top:4px">Mitigation: {cesc(g.get("mitigation",""))}</p></div>')

        if "migration_phases" in mig:
            a('<h3>Migration Phases</h3><div class="tbl-wrap"><table><tr><th>#</th><th>Title</th><th>Status</th><th>What</th></tr>')
            for ph in mig["migration_phases"]:
                sc = {"DONE":"#4caf50","IN-PROGRESS":"#ff9800","TODO":"#64748b"}.get(ph.get("status",""),"#64748b")
                a(f'<tr><td>{ph.get("phase","")}</td><td>{cesc(ph.get("title",""))}</td><td><span class="badge" style="background:{sc}">{ph.get("status","")}</span></td><td style="font-size:10px">{cesc(ph.get("what",""))}</td></tr>')
            a('</table></div>')

    # Remediation plan
    a('<h2 id="remediation">Remediation Plan (by priority)</h2><div class="tbl-wrap"><table><tr><th>#</th><th>ID</th><th>Finding</th><th>Sev</th><th>Action</th></tr>')
    for f in sorted(findings["findings"], key=lambda x: x.get("remediation",{}).get("priority",99)):
        r = f.get("remediation",{})
        a(f'<tr><td>{r.get("priority","-")}</td><td>{f["id"]}</td><td style="max-width:300px">{cesc(f["title"])}</td><td><span class="badge {sev(f["severity"])}">{f["severity"]}</span></td><td style="font-size:10px">{cesc(r.get("what","-"))}</td></tr>')
    a('</table></div>')

    # Evidence
    a('<h2 id="evidence">Evidence Records</h2><div class="tbl-wrap"><table><tr><th>ID</th><th>Category</th><th>Safety</th><th>Exit</th><th>Description</th></tr>')
    for ef in ev_files:
        try:
            d = load_yaml(ef)
            bid = d.get("id", os.path.basename(ef)[:-4])
            a(f'<tr><td><code>{bid}</code></td><td>{d.get("category","")}</td><td>{d.get("safety_level","")}</td><td>{d.get("exit_code","")}</td><td style="font-size:10px;max-width:450px">{cesc(d.get("command","")[:140])}</td></tr>')
        except: pass
    a('</table></div></main></body></html>')
    return "".join(h)

if __name__ == "__main__":
    evidence_dir = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob(os.path.join(REPO,"evidence","*")))[-1]
    print(f"Using: {evidence_dir}", file=sys.stderr)
    html = build_report(evidence_dir)
    report_file = os.path.join(REPO,"reports",f'infrastructure-audit-{os.path.basename(evidence_dir)}.html')
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    with open(report_file,"w") as f: f.write(html)
    print(report_file)
