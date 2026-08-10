#!/usr/bin/env python3
"""Generate professional offline HTML infrastructure audit report from YAML evidence."""
import sys, os, yaml, glob, datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_yaml(path):
    with open(path) as f: return yaml.safe_load(f)

def sev(s):
    m = {"CRITICAL":"crit","HIGH":"high","MEDIUM":"med","LOW":"low","INFO":"info"}
    return m.get(s,"med")

def cesc(s):
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

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

JS = '''<script>
(function(){var btns=document.querySelectorAll('.filter-bar button');
btns.forEach(function(b){b.addEventListener('click',function(){
  btns.forEach(function(x){x.classList.remove('active')});
  b.classList.add('active');
  var sev=b.dataset.sev, cards=document.querySelectorAll('.finding-card');
  cards.forEach(function(c){c.style.display=(!sev||c.classList.contains(sev))?'block':'none'});
})});
document.querySelectorAll('.finding-card').forEach(function(c){
  var cls=c.classList[1]; if(!cls)return;
  c.querySelector('.sev-badge').textContent=cls;
});
})();</script>'''

def build_nav(has_migration):
    items = [
        ('exec-summary','Resumen Ejecutivo'),('infra-overview','Infraestructura'),
        ('architecture','Arquitectura'),('components','Componentes'),
        ('resources','Recursos'),('performance','Rendimiento'),
        ('security','Seguridad'),('reliability','Confiabilidad'),
        ('observability','Observabilidad'),('backup','Respaldos'),
        ('findings','Hallazgos'),
    ]
    if has_migration:
        items.append(('migration','Migracion'))
    items.append(('remediation','Remediacion'))
    items.append(('evidence','Evidencia'))
    links = ''.join(f'<a href="#{id}">{label}</a>' for id, label in items)
    return f'<nav><h2>Contenido</h2>{links}</nav>'

def gen_html(run_dir, findings=None, inventory=None, migration=None):
    run_id = os.path.basename(run_dir)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    has_migration = migration is not None

    host = "unknown"
    if inventory:
        host = inventory.get("host", {}).get("ssh", {}).get("host", "unknown")

    findings_list = findings.get("findings", []) if findings else []
    f_by_sev = {"CRITICAL":0,"HIGH":0,"MEDIUM":0,"LOW":0,"INFO":0}
    for f in findings_list:
        s = f.get("severity","INFO")
        f_by_sev[s] = f_by_sev.get(s, 0) + 1

    html = f'''<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Infrastructure Audit — {host}</title>{CSS}</head><body>
{build_nav(has_migration)}
<main>
<h1>Infrastructure Audit Report</h1>
<p class="sub">Generado: {now} · Host: {host} · Run: {run_id}</p>

<div class="meta">
<div class="meta-item"><div class="val">{f_by_sev['CRITICAL']}</div><div class="lbl">Criticos</div></div>
<div class="meta-item"><div class="val">{f_by_sev['HIGH']}</div><div class="lbl">Altos</div></div>
<div class="meta-item"><div class="val">{f_by_sev['MEDIUM']}</div><div class="lbl">Medios</div></div>
<div class="meta-item"><div class="val">{f_by_sev['LOW']}</div><div class="lbl">Bajos</div></div>
<div class="meta-item"><div class="val">{len(findings_list)}</div><div class="lbl">Total Hallazgos</div></div>
</div>

<h2 id="exec-summary">Resumen Ejecutivo</h2>
<div class="sev-bar">
<span class="crit">CRITICAL: {f_by_sev['CRITICAL']}</span>
<span class="high">HIGH: {f_by_sev['HIGH']}</span>
<span class="med">MEDIUM: {f_by_sev['MEDIUM']}</span>
<span class="low">LOW: {f_by_sev['LOW']}</span>
<span class="info">INFO: {f_by_sev['INFO']}</span>
</div>

<h2 id="findings">Hallazgos</h2>
<div class="filter-bar">
<button class="active" data-sev="">Todos</button>
<button data-sev="crit">Criticos</button>
<button data-sev="high">Altos</button>
<button data-sev="med">Medios</button>
<button data-sev="low">Bajos</button>
</div>
'''
    for f in findings_list:
        s = sev(f.get("severity","INFO"))
        title = cesc(f.get("title","Sin titulo"))
        cat = cesc(f.get("category",""))
        conf = cesc(f.get("confidence","MEDIUM"))
        finding_id = cesc(f.get("id","?"))
        obs = cesc(f.get("observation",""))
        rec = cesc(f.get("recommendation",""))
        impact = cesc(f.get("impact",""))
        evidence = cesc(f.get("evidence",""))
        remediation = f.get("remediation",{})
        html += f'''<div class="finding-card {s}">
<h3>{finding_id} — {title}</h3>
<div class="tags"><span class="badge {s}">{s}</span><span class="badge info">{cat}</span><span class="badge info">conf: {conf}</span></div>
<div class="mg"><span class="l">Observacion</span><span>{obs}</span></div>
<div class="mg"><span class="l">Impacto</span><span>{impact}</span></div>
<div class="mg"><span class="l">Evidencia</span><pre>{evidence}</pre></div>
<div class="rem"><div class="r"><span class="rk">Recomendacion</span><span class="rv">{rec}</span></div></div>
</div>\n'''

    html += f'''
<h2>Evidencia</h2>
<p>Evidencia almacenada en <code>reportes/{run_id}/</code></p>
</main>{JS}</body></html>'''

    return html

def main():
    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} <reportes/run-id> [output.html]", file=sys.stderr)
        sys.exit(2)

    run_dir = sys.argv[1]
    findings_path = os.path.join(run_dir, "findings.yaml")
    inventory_path = os.path.join(run_dir, "inventory.yaml")
    migration_path = os.path.join(run_dir, "migration.yaml")

    findings = load_yaml(findings_path) if os.path.exists(findings_path) else None
    inventory = load_yaml(inventory_path) if os.path.exists(inventory_path) else None
    migration = load_yaml(migration_path) if os.path.exists(migration_path) else None

    html = gen_html(run_dir, findings, inventory, migration)

    run_id = os.path.basename(run_dir)
    out_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(run_dir, f"informe-{run_id}.html")
    with open(out_path, "w") as f:
        f.write(html)
    print(out_path)

if __name__ == "__main__":
    main()
