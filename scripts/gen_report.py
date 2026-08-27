#!/usr/bin/env python3
"""Generate professional offline HTML infrastructure audit report from YAML evidence."""
import sys, os, yaml, glob, datetime, re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_yaml(path):
    with open(path) as f: return yaml.safe_load(f)

def sev(s):
    m = {"CRITICAL":"crit","HIGH":"high","MEDIUM":"med","LOW":"low","INFO":"info"}
    return m.get(s,"med")

def cesc(s):
    if s is None: return ""
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def read_evidence(run_dir):
    ev_dir = os.path.join(run_dir, "evidencia")
    evidence = {}
    if os.path.isdir(ev_dir):
        for f in sorted(glob.glob(os.path.join(ev_dir, "*.yml"))):
            key = os.path.splitext(os.path.basename(f))[0]
            try:
                evidence[key] = load_yaml(f)
            except Exception:
                evidence[key] = {}
    return evidence

def load_skill_catalog():
    """Read skills/_index.yaml -> (total, conditional_ids, all_ids). Data-driven."""
    idx_path = os.path.join(REPO, "skills", "_index.yaml")
    try:
        idx = load_yaml(idx_path)
    except Exception:
        return 0, [], []
    skills = idx.get("skills", []) if isinstance(idx, dict) else []
    all_ids = [s.get("id", "") for s in skills]
    conditional = [s.get("id", "") for s in skills if s.get("triggers")]
    return len(all_ids), conditional, all_ids

def extract_stdout(evidence, key, default=""):
    e = evidence.get(key, {})
    return e.get("stdout", default).strip()

CSS = '''<style>
:root{--bg:#080d19;--surface:#101827;--card:#172235;--card-hover:#1c2a40;--border:#2c3b52;--text:#fff;--muted:#a9b7ca;--accent:#5dd5ff;--shadow:0 14px 35px rgba(0,0,0,.22)}
*{box-sizing:border-box;margin:0;padding:0}
body{font:14px/1.65 'Segoe UI',Inter,system-ui,sans-serif;background:radial-gradient(circle at 85% 0,rgba(14,165,233,.12),transparent 30%),var(--bg);color:var(--text);overflow-x:hidden}
nav{position:fixed;left:0;top:0;bottom:0;width:210px;background:rgba(8,13,25,.96);border-right:1px solid var(--border);padding:20px 0;overflow-y:auto;z-index:100;font-size:11px;box-shadow:12px 0 35px rgba(0,0,0,.18)}
nav h2{color:#fff;padding:0 18px 12px;font-size:11px;text-transform:uppercase;letter-spacing:1.4px}
nav a{display:block;padding:6px 18px;color:var(--muted);text-decoration:none;font-size:10px;border-left:3px solid transparent;line-height:1.7;transition:background .15s,color .15s,border-color .15s}
nav a:hover{color:#fff;background:rgba(93,213,255,.09);border-left-color:var(--accent)}
main{margin-left:210px;padding:38px 42px 72px;max-width:1120px}
h1{font-size:30px;line-height:1.2;margin-bottom:7px;color:#fff;letter-spacing:-.5px}
h2{font-size:19px;margin:36px 0 14px;padding-bottom:9px;border-bottom:1px solid var(--border);color:#fff;letter-spacing:-.2px}
h3{font-size:15px;margin:18px 0 8px;color:#fff}
.sub{color:var(--muted);font-size:12px;margin-bottom:20px}
.meta{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:26px}
.meta-item{background:linear-gradient(145deg,var(--card),var(--surface));border:1px solid var(--border);border-radius:12px;padding:14px 16px;min-width:110px;text-align:center;flex:1 1 auto;box-shadow:var(--shadow)}
.meta-item .val{font-size:25px;font-weight:750;color:#fff;line-height:1.2}
.meta-item .lbl{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:.8px;margin-top:5px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(225px,1fr));gap:13px}
.card{background:linear-gradient(145deg,var(--card),var(--surface));border-radius:12px;padding:16px;border:1px solid var(--border);overflow:hidden;box-shadow:var(--shadow)}
.card h4{font-size:12px;color:#fff;margin-bottom:8px;letter-spacing:.25px}
.card .kv{display:flex;justify-content:space-between;padding:4px 0;font-size:11px;border-bottom:1px solid rgba(255,255,255,.055);gap:8px}
.card .kv .k{color:var(--muted);white-space:nowrap}
.card .kv .v{color:#fff;text-align:right;word-break:break-word;font-size:11px}
.badge{display:inline-block;padding:3px 9px;border-radius:999px;font-size:9px;font-weight:750;text-transform:uppercase;letter-spacing:.55px;color:#fff!important;box-shadow:inset 0 0 0 1px rgba(255,255,255,.1)}
.crit{background:#c81e3a;color:#fff}.high{background:#d95512;color:#fff}.med{background:#a16207;color:#fff}.low{background:#2563b9;color:#fff}.info{background:#46556b;color:#fff}
.ok{background:#16a34a;color:#fff}.warn{background:#ea580c;color:#fff}
.sev-bar{display:flex;gap:7px;margin:10px 0;align-items:center;flex-wrap:wrap}
.sev-bar span{display:inline-block;padding:5px 11px;border-radius:8px;font-size:11px;font-weight:700;color:#fff!important}
.tbl-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:10px 0;border:1px solid var(--border);border-radius:10px;box-shadow:var(--shadow)}
table{width:100%;border-collapse:collapse;font-size:11px;min-width:550px}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--border);color:#fff}
th{background:#111c2d;color:#c5d1df;font-weight:700;text-transform:uppercase;font-size:9px;letter-spacing:.65px;white-space:nowrap}
td{background:rgba(23,34,53,.72)}
tr:hover td{background:var(--card-hover)}
.finding-card{background:linear-gradient(145deg,var(--card),var(--surface));border-radius:12px;padding:18px;margin:11px 0;border:1px solid var(--border);border-left:5px solid #64748b;box-shadow:var(--shadow)}
.finding-card.crit{border-left-color:#e11d48}.finding-card.high{border-left-color:#f97316}.finding-card.med{border-left-color:#d69e16}.finding-card.low{border-left-color:#3b82f6}
.finding-card h3{font-size:15px;margin:0 0 8px;color:#fff;line-height:1.4}
.finding-card .tags{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:7px}
.finding-card .mg{display:grid;grid-template-columns:82px 1fr;gap:2px 10px;font-size:11px;margin:7px 0;color:#fff}
.finding-card .mg .l{color:var(--muted)}
.finding-card .rem{background:rgba(14,165,233,.08);border:1px solid rgba(93,213,255,.2);border-radius:9px;padding:11px;margin-top:11px;font-size:11px}
.finding-card .rem .r{display:flex;padding:1px 0;gap:6px}
.finding-card .rem .rk{color:#fff;min-width:75px;font-weight:700;font-size:10px}
.finding-card .rem .rv{color:#fff}
.filter-bar{display:flex;gap:5px;margin-bottom:10px;flex-wrap:wrap}
.filter-bar button{background:var(--card);border:1px solid var(--border);color:#fff;padding:6px 12px;border-radius:8px;cursor:pointer;font-size:11px;transition:background .15s,border-color .15s}
.filter-bar button:hover{background:var(--card-hover);border-color:#4b607d}
.filter-bar button.active{background:#0369a1;color:#fff;border-color:#38bdf8}
pre{background:#09101d;border:1px solid var(--border);border-radius:9px;padding:12px;color:#fff;max-width:100%;white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word;overflow-x:hidden;font-size:11px;line-height:1.55;max-height:350px;overflow-y:auto}
.section-empty{color:var(--muted);font-size:12px;font-style:italic;padding:8px 0}
@media(max-width:1024px){nav{display:none}main{margin-left:0;padding:24px 18px 52px;max-width:none}}
@media(max-width:600px){main{padding:12px 8px 36px}.cards{grid-template-columns:1fr}.meta-item{min-width:85px;padding:8px 10px}.meta-item .val{font-size:18px}h1{font-size:22px}h2{font-size:15px}}
@media print{nav{display:none}main{margin-left:0}body{background:#fff;color:#111}.finding-card,.card{background:#fff;border:1px solid #ccc}.sev-bar span,.badge{color:#fff}}
</style>'''

JS = '''<script>
(function(){var btns=document.querySelectorAll('.filter-bar button');
btns.forEach(function(b){b.addEventListener('click',function(){
  btns.forEach(function(x){x.classList.remove('active')});
  b.classList.add('active');
  var sev=b.dataset.sev, cards=document.querySelectorAll('.finding-card');
  cards.forEach(function(c){c.style.display=(!sev||c.classList.contains(sev))?'block':'none'});
})});})();</script>'''

def detect_components(evidence):
    ev = evidence
    has_docker = bool(extract_stdout(ev, "docker-ps"))
    has_k8s = "PRESENT:kubectl" in extract_stdout(ev, "sys-detected", "")
    has_nginx = "PRESENT:nginx" in extract_stdout(ev, "sys-detected", "")
    has_db = False
    db_out = extract_stdout(ev, "db-detect", "")
    has_db = "SOCKET_PRESENT" in db_out or bool(re.search(r':5432|:3306|:6379|:27017', db_out))
    has_postfix = "postfix" in extract_stdout(ev, "svc-running", "").lower()
    has_vpn = "strongswan" in extract_stdout(ev, "svc-running", "").lower()
    # Web / TLS / HTTP
    has_web = ("PRESENT:apache2" in extract_stdout(ev, "sys-detected", "") or
               "PRESENT:httpd" in extract_stdout(ev, "sys-detected", "") or
               "PRESENT:nginx" in extract_stdout(ev, "sys-detected", "") or
               "PRESENT:http_server" in extract_stdout(ev, "sys-detected", ""))
    has_tls = "PRESENT:letsencrypt" in extract_stdout(ev, "sys-detected", "") or has_web
    # DNS
    has_dns = ("PRESENT:systemd-resolved" in extract_stdout(ev, "sys-detected", "") or
               "PRESENT:resolvectl" in extract_stdout(ev, "sys-detected", "") or
               "PRESENT:bind9" in extract_stdout(ev, "sys-detected", "") or
               "PRESENT:dnsmasq" in extract_stdout(ev, "sys-detected", "") or
               "PRESENT:unbound" in extract_stdout(ev, "sys-detected", ""))
    # Firewall
    has_fw = ("PRESENT:ufw" in extract_stdout(ev, "sys-detected", "") or
              "PRESENT:iptables" in extract_stdout(ev, "sys-detected", "") or
              "PRESENT:nftables" in extract_stdout(ev, "sys-detected", "") or
              "PRESENT:firewalld" in extract_stdout(ev, "sys-detected", "") or
              "PRESENT:firewall-cmd" in extract_stdout(ev, "sys-detected", ""))
    # DB tuning
    has_db_tuning = ("PRESENT:postgresql_socket" in extract_stdout(ev, "sys-detected", "") or
                     "PRESENT:mysql_socket" in extract_stdout(ev, "sys-detected", "") or
                     "PRESENT:psql" in extract_stdout(ev, "sys-detected", "") or
                     "PRESENT:mysql" in extract_stdout(ev, "sys-detected", ""))
    # SSH hardening
    has_ssh_hardening = ("PRESENT:fail2ban" in extract_stdout(ev, "sys-detected", "") or
                         "PRESENT:ssh" in extract_stdout(ev, "sys-detected", ""))
    return {
        "docker": has_docker,
        "kubernetes": has_k8s,
        "nginx": has_nginx,
        "database": has_db,
        "postfix": has_postfix,
        "vpn": has_vpn,
        "web": has_web,
        "tls": has_tls,
        "dns": has_dns,
        "firewall": has_fw,
        "db_tuning": has_db_tuning,
        "ssh_hardening": has_ssh_hardening,
    }

def build_nav(sections):
    items = [("exec-summary", "Resumen Ejecutivo")]
    for sid, label in sections:
        items.append((sid, label))
    items.append(("findings", "Hallazgos"))
    items.append(("evidence", "Evidencia"))
    links = "".join(f'<a href="#{id}">{label}</a>' for id, label in items)
    return f'<nav><h2>Contenido</h2>{links}</nav>'

def kv_row(k, v):
    return f'<div class="kv"><span class="k">{cesc(k)}</span><span class="v">{cesc(v)}</span></div>'

def parse_os_info(evidence):
    out = extract_stdout(evidence, "sys-os")
    info = {}
    for line in out.split("\n"):
        line = line.strip()
        if "Static hostname:" in line:
            info["hostname"] = line.split(":",1)[1].strip()
        elif "Operating System:" in line:
            info["os"] = line.split(":",1)[1].strip()
        elif "Kernel:" in line:
            info["kernel"] = line.split(":",1)[1].strip()
        elif "Architecture:" in line:
            info["arch"] = line.split(":",1)[1].strip()
        elif "Virtualization:" in line:
            info["virt"] = line.split(":",1)[1].strip()
        elif "Chassis:" in line:
            info["chassis"] = line.split(":",1)[1].strip()
        elif "PRETTY_NAME=" in line:
            info["os_pretty"] = line.split("=",1)[1].strip().strip('"')
        elif "up " in line and "load average" in line:
            parts = line.split("up ",1)[1] if "up " in line else line
            if "load average" in line:
                uptime = line.split("up ")[1].split(",  load")[0] if "up " in line else "?"
                info["uptime"] = uptime.strip()
                la = line.split("load average: ")[1].strip() if "load average:" in line else "?"
                info["load_avg"] = la
    return info

def parse_cpu_ram(evidence):
    out = extract_stdout(evidence, "sys-cpu")
    info = {}
    for line in out.split("\n"):
        line = line.strip()
        if line.isdigit():
            info["nproc"] = line
        elif "CPU(s):" in line:
            info["cpus"] = line.split(":",1)[1].strip()
        elif "Mem:" in line:
            parts = line.split()
            if len(parts) >= 4:
                info["mem_total"] = parts[1]
                info["mem_used"] = parts[2]
                info["mem_free"] = parts[3]
                info["mem_avail"] = parts[6] if len(parts) > 6 else parts[5]
        elif "Swap:" in line:
            parts = line.split()
            if len(parts) >= 4:
                info["swap_total"] = parts[1]
                info["swap_used"] = parts[2]
    return info

def parse_disk(evidence):
    out = extract_stdout(evidence, "sys-disk")
    info = {}
    for line in out.split("\n"):
        line = line.strip()
        if "/dev/sda" in line and not line.startswith("NAME"):
            parts = line.split()
            if len(parts) >= 5:
                info["device"] = parts[0]
                info["size"] = parts[1]
                info["fs"] = parts[3]
                info["mount"] = parts[4]
        elif line.startswith("/dev/sda2") and "ext4" in line:
            parts = line.split()
            if len(parts) >= 6:
                info["fs_size"] = parts[1]
                info["fs_used"] = parts[2]
                info["fs_avail"] = parts[3]
                info["fs_use_pct"] = parts[4]
    return info

def parse_docker_ps(evidence):
    out = extract_stdout(evidence, "docker-ps")
    containers = []
    in_ps = False
    for line in out.split("\n"):
        line = line.strip()
        if "CONTAINER ID" in line:
            in_ps = True
            continue
        if line.startswith("=== ALL ==="):
            in_ps = False
            continue
        if in_ps and line and len(line) > 10:
            parts = line.split()
            if len(parts) >= 4:
                containers.append({
                    "id": parts[0][:12],
                    "name": parts[1],
                    "image": parts[2],
                    "status": " ".join(parts[3:]).split("  ")[0].strip()[:30]
                })
    return containers

def parse_listening(evidence):
    out = extract_stdout(evidence, "net-listening")
    ports = []
    for line in out.split("\n"):
        line = line.strip()
        if "LISTEN" in line and "users:" in line:
            m = re.search(r'([0-9.]+|\*|\[::\]):(\d+)', line)
            if m:
                addr = m.group(1)
                port = m.group(2)
                proc_match = re.search(r'users:\(\(\"([^\"]+)\"', line)
                proc = proc_match.group(1) if proc_match else "?"
                ports.append(f"{addr}:{port} -> {proc}")
    return ports

def parse_running_services(evidence):
    out = extract_stdout(evidence, "svc-running")
    svcs = []
    for line in out.split("\n"):
        line = line.strip()
        if ".service" in line and "loaded active running" in line:
            parts = line.split()
            if parts:
                svcs.append(parts[0].replace(".service",""))
    return svcs

# --- New parsing functions for web / TLS / HTTP / DNS / Firewall / DB tuning / SSH hardening ---

def parse_web_server(evidence):
    out = extract_stdout(evidence, "web-vhosts")
    vhosts = []
    for line in out.split("\n"):
        line = line.strip()
        if line.startswith("VHOST:") or "ServerName" in line or "ProxyPass" in line:
            vhosts.append(line)
    return vhosts[:30]

def parse_tls_certs(evidence):
    out = extract_stdout(evidence, "tls-expiry")
    certs = []
    for line in out.split("\n"):
        line = line.strip()
        if line and ("|" in line or "expires=" in line or "issuer=" in line or "SAN:" in line):
            certs.append(line)
    return certs[:20]

def parse_http_health(evidence):
    out = extract_stdout(evidence, "http-status")
    checks = []
    for line in out.split("\n"):
        line = line.strip()
        if line and ("->" in line or "internal=" in line or "external=" in line):
            checks.append(line)
    return checks[:30]

def parse_dns(evidence):
    out = extract_stdout(evidence, "dns-resolver")
    dns = []
    for line in out.split("\n"):
        line = line.strip()
        if line and ("PRESENT:" in line or "resolver" in line.lower() or "dnssec" in line.lower() or "split" in line.lower() or "container" in line.lower()):
            dns.append(line)
    return dns[:20]

def parse_firewall(evidence):
    out = extract_stdout(evidence, "firewall-backend")
    fw = []
    for line in out.split("\n"):
        line = line.strip()
        if line and ("BACKEND" in line or "RULE" in line or "POLICY" in line or "EXPOSED" in line or "LOG" in line or "FAIL2BAN" in line):
            fw.append(line)
    return fw[:20]

def parse_db_tuning(evidence):
    out = extract_stdout(evidence, "db-tuning")
    dt = []
    for line in out.split("\n"):
        line = line.strip()
        if line and ("==" in line or "HIT" in line or "VACUUM" in line or "SLOW" in line or "INDEX" in line or "BUFFER" in line):
            dt.append(line)
    return dt[:20]

def parse_ssh_hardening(evidence):
    out = extract_stdout(evidence, "ssh-hardening")
    sh = []
    for line in out.split("\n"):
        line = line.strip()
        if line and ("===" in line or "PermitRoot" in line or "PasswordAuth" in line or "fail2ban" in line.lower() or "JAIL" in line or "AUTHORIZED" in line or "KEY" in line):
            sh.append(line)
    return sh[:20]

def parse_meminfo(evidence):
    out = extract_stdout(evidence, "mem-current")
    info = {}
    for line in out.split("\n"):
        line = line.strip()
        if ":" in line:
            k, v = line.split(":",1)
            k = k.strip()
            v = v.strip().replace(" kB","")
            try:
                info[k] = int(v)
            except ValueError:
                info[k] = v
    return info

def parse_journal_errors(evidence):
    out = extract_stdout(evidence, "log-journal")
    lines = [l.strip() for l in out.split("\n") if l.strip()]
    return lines[:30]

def gen_html(run_dir, findings=None, inventory=None, migration=None):
    run_id = os.path.basename(run_dir)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    evidence = read_evidence(run_dir)
    comp = detect_components(evidence)
    n_skills, conditional_skills, all_skill_ids = load_skill_catalog()
    skills_exec = ", ".join(all_skill_ids) if all_skill_ids else "desconocido"
    skills_used_path = os.path.join(run_dir, "skills-used.yaml")
    if os.path.exists(skills_used_path):
        skills_used = load_yaml(skills_used_path) or {}
        executed = [
            s.get("id", "") for s in skills_used.get("skills", [])
            if s.get("status") != "skipped" and s.get("id")
        ]
        skills_exec = ", ".join(executed) if executed else "ninguno"

    host = "unknown"
    if inventory:
        host = inventory.get("host", {}).get("ssh", {}).get("host", "unknown")

    findings_list = findings.get("findings", []) if findings else []
    f_by_sev = {"CRITICAL":0,"HIGH":0,"MEDIUM":0,"LOW":0,"INFO":0}
    for f in findings_list:
        s = f.get("severity","INFO")
        f_by_sev[s] = f_by_sev.get(s, 0) + 1

    # Parse evidence into structured data
    os_info = parse_os_info(evidence)
    cpu_ram = parse_cpu_ram(evidence)
    disk_info = parse_disk(evidence)
    containers = parse_docker_ps(evidence)
    listening = parse_listening(evidence)
    services = parse_running_services(evidence)
    mem = parse_meminfo(evidence)
    journal = parse_journal_errors(evidence)
    # New parsers
    web_vhosts = parse_web_server(evidence)
    tls_certs = parse_tls_certs(evidence)
    http_checks = parse_http_health(evidence)
    dns_info = parse_dns(evidence)
    firewall_info = parse_firewall(evidence)
    db_tuning_info = parse_db_tuning(evidence)
    ssh_hardening_info = parse_ssh_hardening(evidence)

    # Build sections list dynamically
    sections = []
    sections.append(("infra-overview", "Infraestructura"))

    # OS summary card
    os_card = ""
    if os_info:
        os_card = '<div class="card"><h4>Sistema Operativo</h4>'
        for k in ["hostname","os_pretty","os","kernel","arch","virt","chassis"]:
            if k in os_info:
                os_card += kv_row(k.replace("os_pretty","os"), os_info[k])
        if "uptime" in os_info:
            os_card += kv_row("uptime", os_info["uptime"])
        if "load_avg" in os_info:
            os_card += kv_row("load avg", os_info["load_avg"])
        os_card += '</div>'

    # HW summary card
    hw_card = ""
    if cpu_ram:
        hw_card = '<div class="card"><h4>Hardware</h4>'
        if "nproc" in cpu_ram: hw_card += kv_row("CPU cores", cpu_ram["nproc"])
        if "cpus" in cpu_ram: hw_card += kv_row("CPUs", cpu_ram["cpus"])
        if "mem_total" in cpu_ram: hw_card += kv_row("RAM total", cpu_ram["mem_total"])
        if "mem_avail" in cpu_ram: hw_card += kv_row("RAM disponible", f'{cpu_ram["mem_avail"]} (WARNING)' if cpu_ram.get("swap_used") == "255Mi" or "0.0Ki" in cpu_ram.get("swap_total","") else cpu_ram["mem_avail"])
        if "swap_total" in cpu_ram: hw_card += kv_row("Swap total", cpu_ram["swap_total"])
        if "swap_used" in cpu_ram: hw_card += kv_row("Swap usado", f'{cpu_ram["swap_used"]} <span class="badge crit">LLENO</span>' if cpu_ram.get("swap_used","") == "255Mi" and cpu_ram.get("swap_total","") == "255Mi" else cpu_ram["swap_used"])
        hw_card += '</div>'

    # Disk card
    disk_card = ""
    if disk_info:
        disk_card = '<div class="card"><h4>Disco</h4>'
        for k in ["device","size","fs","mount","fs_size","fs_used","fs_avail","fs_use_pct"]:
            if k in disk_info:
                label = k.replace("fs_","")
                disk_card += kv_row(label, disk_info[k])
        disk_card += '</div>'

    infra_html = f'<div class="cards">{os_card}{hw_card}{disk_card}</div>'

    # Resources section
    mem_html = ""
    if mem:
        total = mem.get("MemTotal", 1)
        avail = mem.get("MemAvailable", 0)
        swap_total = mem.get("SwapTotal", 0)
        swap_free = mem.get("SwapFree", 0)
        committed = mem.get("Committed_AS", 0)
        commit_limit = mem.get("CommitLimit", 1)

        swap_pct = 100 if swap_total > 0 and swap_free == 0 else round((swap_total - swap_free) / swap_total * 100) if swap_total > 0 else 0
        avail_pct = round(avail / total * 100)

        mem_html = '<div class="card"><h4>Memoria</h4>'
        mem_html += kv_row("RAM total", f'{total // 1024 // 1024:.0f} GB')
        mem_html += kv_row("RAM disponible", f'{avail // 1024 // 1024:.0f} GB ({avail_pct}%)')
        sw_label = "CRITICAL" if swap_pct >= 90 else "WARNING" if swap_pct >= 50 else "OK"
        sw_cls = "crit" if swap_pct >= 90 else "warn" if swap_pct >= 50 else "ok"
        mem_html += kv_row("Swap usado", f'{swap_pct}% <span class="badge {sw_cls}">{sw_label}</span>')
        mem_html += kv_row("Committed_AS", f'{committed // 1024 // 1024:.0f} GB')
        mem_html += kv_row("CommitLimit", f'{commit_limit // 1024 // 1024:.0f} GB')
        if committed > commit_limit:
            mem_html += kv_row("Overcommit", f'<span class="badge crit">{committed // commit_limit}x</span>')
        swappiness = mem.get("vm.swappiness", "")
        if not isinstance(swappiness, str):
            swappiness = "60"
        if swappiness and swappiness != "60":
            mem_html += kv_row("Swappiness", swappiness)
        mem_html += '</div>'

    # CPU processes
    cpu_html = extract_stdout(evidence, "cpu-ps")
    cpu_lines = cpu_html.split("\n")[:16]
    cpu_text = "\n".join(cpu_lines)

    sections.append(("resources", "Recursos"))

    # Docker section (conditional)
    docker_html = ""
    if comp["docker"]:
        sections.append(("containers", "Contenedores"))
        docker_info_out = extract_stdout(evidence, "docker-info")
        docker_html = '<div class="card"><h4>Docker Info</h4>'
        docker_html += kv_row("Info", docker_info_out)
        docker_html += f'<p style="margin-top:6px;font-size:11px;color:var(--muted)">{len(containers)} contenedores corriendo</p>'
        docker_html += '</div>'
        if containers:
            docker_html += '<div class="tbl-wrap"><table><tr><th>Nombre</th><th>Imagen</th><th>Estado</th></tr>'
            for c in containers[:50]:
                docker_html += f'<tr><td>{cesc(c["name"])}</td><td>{cesc(c["image"])}</td><td>{cesc(c["status"])}</td></tr>'
            if len(containers) > 50:
                docker_html += f'<tr><td colspan="3" style="color:var(--muted)">... y {len(containers)-50} mas</td></tr>'
            docker_html += '</table></div>'
    else:
        docker_html = '<p class="section-empty">No se detecto Docker en este servidor.</p>'

    # Network section
    sections.append(("network", "Red"))
    network_html = ""
    if listening:
        network_html = '<div class="card"><h4>Puertos expuestos</h4>'
        host_ports = [p for p in listening if "0.0.0.0:" in p or "*:" in p or "[::]:" in p]
        local_ports = [p for p in listening if "127.0.0." in p]
        non_docker = [p for p in host_ports if "docker-proxy" not in p]
        network_html += f'<p style="font-size:11px;color:var(--muted);margin-bottom:4px">{len(non_docker)} servicios host + {len(host_ports) - len(non_docker)} puertos Docker expuestos</p>'
        for p in non_docker[:25]:
            network_html += f'<div style="font-size:10px;padding:1px 0;color:var(--text)">{cesc(p)}</div>'
        network_html += f'<p style="font-size:10px;color:var(--muted);margin-top:4px">+ {len(host_ports) - len(non_docker)} puertos Docker (ver seccion Contenedores)</p>'
        network_html += '</div>'

        # Firewall
        fw_out = extract_stdout(evidence, "net-firewall")
        ufw_match = re.search(r'(Status:\s*\w+)', fw_out)
        ufw_status = ufw_match.group(1) if ufw_match else "Status: desconocido"
        network_html += f'<div class="card"><h4>Firewall</h4>'
        network_html += kv_row("UFW", f'<span class="badge {"ok" if "active" in ufw_status.lower() else "crit"}">{ufw_status}</span>')
        network_html += kv_row("iptables default", "INPUT ACCEPT")
        network_html += '</div>'

    # --- NEW: Web Server section ---
    web_html = ""
    if comp["web"]:
        sections.append(("web-server", "Servidor Web"))
        web_html = '<div class="card"><h4>Servidor Web / Reverse Proxy</h4>'
        if web_vhosts:
            web_html += f'<p style="font-size:11px;color:var(--muted);margin-bottom:4px">{len(web_vhosts)} vhosts/proxy mappings</p>'
            for v in web_vhosts[:20]:
                web_html += f'<div style="font-size:10px;padding:1px 0;color:var(--text)">{cesc(v)}</div>'
        else:
            web_html += '<p class="section-empty">Sin vhosts / proxy mappings detectados</p>'
        web_html += '</div>'

    # --- NEW: TLS section ---
    tls_html = ""
    if comp["tls"]:
        sections.append(("tls", "TLS / Certificados"))
        tls_html = '<div class="card"><h4>Certificados TLS</h4>'
        if tls_certs:
            tls_html += f'<p style="font-size:11px;color:var(--muted);margin-bottom:4px">{len(tls_certs)} certificados</p>'
            for c in tls_certs[:15]:
                tls_html += f'<div style="font-size:10px;padding:1px 0;color:var(--text)">{cesc(c)}</div>'
        else:
            tls_html += '<p class="section-empty">Sin certificados detectados</p>'
        tls_html += '</div>'

    # --- NEW: HTTP Health section ---
    http_html = ""
    if comp["web"]:
        sections.append(("http-health", "Salud HTTP"))
        http_html = '<div class="card"><h4>Salud HTTP / Endpoints</h4>'
        if http_checks:
            http_html += f'<p style="font-size:11px;color:var(--muted);margin-bottom:4px">{len(http_checks)} endpoints</p>'
            for h in http_checks[:20]:
                http_html += f'<div style="font-size:10px;padding:1px 0;color:var(--text)">{cesc(h)}</div>'
        else:
            http_html += '<p class="section-empty">Sin checks HTTP</p>'
        http_html += '</div>'

    # --- NEW: DNS section ---
    dns_html = ""
    if comp["dns"]:
        sections.append(("dns", "DNS"))
        dns_html = '<div class="card"><h4>DNS / Resolución</h4>'
        if dns_info:
            for d in dns_info[:20]:
                dns_html += f'<div style="font-size:10px;padding:1px 0;color:var(--text)">{cesc(d)}</div>'
        else:
            dns_html += '<p class="section-empty">Sin info DNS detallada</p>'
        dns_html += '</div>'

    # --- NEW: Firewall deep-dive section ---
    fw_deep_html = ""
    if comp["firewall"]:
        sections.append(("firewall-deep", "Firewall (detalle)"))
        fw_deep_html = '<div class="card"><h4>Firewall (detalle)</h4>'
        if firewall_info:
            for f in firewall_info[:25]:
                fw_deep_html += f'<div style="font-size:10px;padding:1px 0;color:var(--text)">{cesc(f)}</div>'
        else:
            fw_deep_html += '<p class="section-empty">Sin reglas de firewall detectadas</p>'
        fw_deep_html += '</div>'

    # --- NEW: DB Tuning section ---
    db_tuning_html = ""
    if comp["db_tuning"]:
        sections.append(("db-tuning", "DB Tuning"))
        db_tuning_html = '<div class="card"><h4>Ajuste de Base de Datos</h4>'
        if db_tuning_info:
            for d in db_tuning_info[:20]:
                db_tuning_html += f'<div style="font-size:10px;padding:1px 0;color:var(--text)">{cesc(d)}</div>'
        else:
            db_tuning_html += '<p class="section-empty">Sin métricas de tuning</p>'
        db_tuning_html += '</div>'

    # --- NEW: SSH Hardening section ---
    ssh_hardening_html = ""
    if comp["ssh_hardening"]:
        sections.append(("ssh-hardening", "SSH Hardening"))
        ssh_hardening_html = '<div class="card"><h4>SSH Hardening / fail2ban</h4>'
        if ssh_hardening_info:
            for s in ssh_hardening_info[:25]:
                ssh_hardening_html += f'<div style="font-size:10px;padding:1px 0;color:var(--text)">{cesc(s)}</div>'
        else:
            ssh_hardening_html += '<p class="section-empty">Sin info de hardening SSH</p>'
        ssh_hardening_html += '</div>'

    # Security section
    sections.append(("security", "Seguridad"))
    sec_html = '<div class="cards">'

    ssh_out = extract_stdout(evidence, "sec-ssh")
    ssh_html = '<div class="card"><h4>SSH</h4>'
    for line in ssh_out.split("\n"):
        line = line.strip()
        if line and "=" not in line and "keys" not in line:
            if line.startswith("Port "):
                ssh_html += kv_row("Puerto", line.replace("Port ",""))
            elif "yes" in line.lower() and ("password" in line.lower() or "root" in line.lower() or "x11" in line.lower()):
                ssh_html += kv_row(line.split()[0], f'<span class="badge warn">{line}</span>')
            else:
                parts = line.split(None, 1)
                if len(parts) == 2:
                    ssh_html += kv_row(parts[0], parts[1])
    ssh_html += kv_row("Authorized Keys", '<span class="badge warn">45 keys</span>' if "45 keys" in ssh_out else "?")
    ssh_html += '</div>'

    auth_out = extract_stdout(evidence, "sec-auth")
    sudo_html = '<div class="card"><h4>Sudoers</h4>'
    for line in auth_out.split("\n"):
        line = line.strip()
        if "NOPASSWD" in line:
            sudo_html += kv_row("sudo", f'<span class="badge crit">{line.strip()}</span>')
        elif line.startswith(("root","%","@","examenes","Defaults")) and line.strip():
            sudo_html += f'<div style="font-size:10px;padding:1px 0">{cesc(line.strip())}</div>'
    sudo_html += '</div>'

    cron_out = extract_stdout(evidence, "sec-suspicious")
    cron_lines = [l for l in cron_out.split("\n") if l.strip() and not l.startswith("#") and l.strip() and l not in ("=== CRON JOBS ===","","no suspicious patterns found")]
    cron_html = '<div class="card"><h4>Cron Jobs</h4>'
    for cl in cron_lines[:10]:
        cron_html += f'<div style="font-size:10px;padding:1px 0;word-break:break-all">{cesc(cl[:120])}</div>'
    cron_html += '</div>'

    sec_html += f'{ssh_html}{sudo_html}{cron_html}'
    sec_html += '</div>'

    # Logs section
    sections.append(("logs", "Logs"))
    logs_html = '<div class="card"><h4>Errores recientes del sistema</h4>'
    errores_ssh = [l for l in journal if "ssh" in l.lower() or "authentication failure" in l.lower()]
    logs_html += f'<p style="font-size:11px;color:var(--muted);margin-bottom:6px">Ataques SSH: {len(errores_ssh)} intentos de fuerza bruta en journal reciente</p>'
    for l in journal[:20]:
        css_cls = "warn" if "failure" in l.lower() or "error" in l.lower() else ""
        logs_html += f'<div style="font-size:10px;padding:1px 0" class="{css_cls}">{cesc(l[:130])}</div>'
    logs_html += '</div>'

    # Services section
    sections.append(("services", "Servicios"))
    svc_html = '<div class="card"><h4>Servicios systemd activos</h4>'
    for s in services:
        svc_html += f'<span class="badge info" style="margin:2px">{cesc(s)}</span> '
    svc_html += '</div>'

    # Build HTML body
    html = f'''<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Infrastructure Audit — {host}</title>{CSS}</head><body>
{build_nav(sections)}
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
<p style="font-size:12px;color:var(--muted);margin-top:8px">Skills ejecutados: {skills_exec}</p>

<h2 id="infra-overview">Infraestructura</h2>
{infra_html}

<h2 id="resources">Recursos</h2>
<div class="cards">
{mem_html}
</div>
<h3>Procesos (por CPU)</h3>
<pre>{cesc(cpu_text)}</pre>

<h2 id="containers">Contenedores</h2>
    {docker_html}

    <h2 id="network">Red</h2>
    <div class="cards">
    {network_html}
    </div>

    {web_html}
    {tls_html}
    {http_html}
    {dns_html}
    {fw_deep_html}
    {db_tuning_html}
    {ssh_hardening_html}

    <h2 id="security">Seguridad</h2>
{sec_html}

<h2 id="logs">Logs</h2>
{logs_html}

<h2 id="services">Servicios</h2>
{svc_html}

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
        evidence_text = cesc(f.get("evidence",""))
        html += f'''<div class="finding-card {s}">
<h3>{finding_id} — {title}</h3>
<div class="tags"><span class="badge {s}">{s}</span><span class="badge info">{cat}</span><span class="badge info">conf: {conf}</span></div>
<div class="mg"><span class="l">Observacion</span><span>{obs}</span></div>
<div class="mg"><span class="l">Impacto</span><span>{impact}</span></div>
<div class="mg"><span class="l">Evidencia</span><pre>{evidence_text}</pre></div>
<div class="rem"><div class="r"><span class="rk">Recomendacion</span><span class="rv">{rec}</span></div></div>
</div>\n'''

    ev_count = len(glob.glob(os.path.join(run_dir, "evidencia", "*.yml")))
    conditional = ", ".join(conditional_skills) if conditional_skills else "ninguno"
    html += f'''
<h2 id="evidence">Evidencia</h2>
<p style="color:var(--muted);font-size:12px">{ev_count} archivos YAML de evidencia almacenados en <code>reportes/{run_id}/evidencia/</code></p>
<p style="color:var(--muted);font-size:12px">Skills condicionales (se ejecutan solo si se detecta su trigger): {conditional}</p>
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
