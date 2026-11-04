# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, render_template_string, session, redirect
import requests
import urllib3
import sqlite3
from datetime import datetime
import hashlib
import json
from werkzeug.security import generate_password_hash, check_password_hash
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "ultra_gizli_siber_anahtar_2024")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
DB_FILE = "siber_karargah.db"
API_BASE = "https://violetpanel.cc/furkanapi"

def init_db():
    c = sqlite3.connect(DB_FILE)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT,
        query_type TEXT, query_param TEXT, ip TEXT, timestamp TEXT, status TEXT
    );
    CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
    """)
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('maintenance', '0')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('broadcast', 'Sisteme hoş geldiniz.')")
    c.commit()
    c.close()

init_db()

def log_query(uid, uname, q_type, param, ip, status):
    c = sqlite3.connect(DB_FILE)
    c.execute("INSERT INTO logs (user_id, username, query_type, query_param, ip, timestamp, status) VALUES (?,?,?,?,?,?,?)",
              (uid, uname, q_type, param, ip, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), status))
    c.commit()
    c.close()

def get_setting(k):
    c = sqlite3.connect(DB_FILE)
    r = c.execute("SELECT value FROM settings WHERE key=?", (k,)).fetchone()
    c.close()
    return r[0] if r else ""

def set_setting(k, v):
    c = sqlite3.connect(DB_FILE)
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (k, v))
    c.commit()
    c.close()

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>ShopSphere | Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #09090b;
            --surface: #18181b;
            --surface-hover: #27272a;
            --border: #27272a;
            --text-main: #f4f4f5;
            --text-muted: #a1a1aa;
            --primary: #6366f1;
            --primary-hover: #4f46e5;
            --success: #22c55e;
            --danger: #ef4444;
        }
        
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; -webkit-tap-highlight-color: transparent; outline: none; }
        body { background-color: var(--bg); color: var(--text-main); min-height: 100vh; display: flex; }
        
        .auth-wrapper { display: flex; align-items: center; justify-content: center; width: 100%; padding: 20px; background: radial-gradient(circle at top right, rgba(99, 102, 241, 0.15), transparent 40%); }
        .auth-card { background: var(--surface); border: 1px solid var(--border); padding: 40px; border-radius: 16px; width: 100%; max-width: 400px; box-shadow: 0 20px 40px rgba(0,0,0,0.4); }
        .auth-card h1 { font-size: 24px; font-weight: 700; margin-bottom: 8px; text-align: center; }
        .auth-card p { color: var(--text-muted); font-size: 14px; text-align: center; margin-bottom: 30px; }
        .form-group { margin-bottom: 16px; }
        .form-group label { display: block; font-size: 13px; font-weight: 500; color: var(--text-muted); margin-bottom: 6px; }
        .form-group input { width: 100%; padding: 12px 16px; background: var(--bg); border: 1px solid var(--border); border-radius: 8px; color: var(--text-main); font-size: 14px; transition: 0.2s; }
        .form-group input:focus { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(99,102,241,0.2); }
        .btn { width: 100%; padding: 12px; background: var(--primary); color: #fff; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; transition: 0.2s; }
        .btn:hover { background: var(--primary-hover); }
        .auth-switch { text-align: center; margin-top: 20px; font-size: 13px; color: var(--text-muted); cursor: pointer; }
        .auth-switch span { color: var(--primary); font-weight: 600; }

        .app-layout { display: flex; width: 100%; min-height: 100vh; }
        
        .sidebar-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); backdrop-filter: blur(2px); z-index: 998; opacity: 0; pointer-events: none; transition: 0.3s; }
        .sidebar-overlay.show { opacity: 1; pointer-events: auto; }
        
        .sidebar { 
            width: 260px; background: var(--surface); border-right: 1px solid var(--border); 
            display: flex; flex-direction: column; position: fixed; height: 100vh; 
            left: 0; top: 0; z-index: 999; transform: translateX(-100%); 
            transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1); overflow-y: auto;
        }
        .sidebar.open { transform: translateX(0); }
        
        .sidebar-header { padding: 20px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }
        .sidebar-header h2 { font-size: 16px; font-weight: 700; color: var(--text-main); }
        
        .sidebar-nav { padding: 15px 10px; flex: 1; }
        .nav-title { font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin: 15px 10px 8px; }
        .nav-item { display: flex; align-items: center; padding: 10px 12px; border-radius: 8px; color: var(--text-muted); font-size: 14px; font-weight: 500; cursor: pointer; margin-bottom: 2px; transition: 0.2s; }
        .nav-item:hover { background: var(--surface-hover); color: var(--text-main); }
        .nav-item.active { background: rgba(99,102,241,0.1); color: var(--primary); font-weight: 600; }
        
        .main-content { flex: 1; display: flex; flex-direction: column; min-width: 0; transition: 0.3s; }
        
        .topbar { height: 64px; background: var(--surface); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 20px; position: sticky; top: 0; z-index: 50; }
        .topbar-left { display: flex; align-items: center; gap: 15px; }
        
        .hamburger { display: flex; flex-direction: column; justify-content: space-around; width: 24px; height: 20px; cursor: pointer; }
        .hamburger span { width: 100%; height: 2px; background: var(--text-main); border-radius: 2px; transition: 0.3s; }
        
        .user-badge { font-size: 13px; font-weight: 500; color: var(--text-muted); display: flex; align-items: center; gap: 10px; }
        .logout-btn { background: transparent; border: 1px solid var(--border); color: var(--text-main); padding: 6px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; transition: 0.2s; }
        .logout-btn:hover { background: var(--surface-hover); }

        .content-area { padding: 24px; max-width: 1000px; margin: 0 auto; width: 100%; display: flex; flex-direction: column; gap: 24px; }
        
        .card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 24px; }
        .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid var(--border); }
        .card-title { font-size: 16px; font-weight: 600; }
        
        .form-row { display: flex; flex-direction: column; gap: 16px; margin-bottom: 20px; }
        .input-wrapper { display: flex; flex-direction: column; gap: 6px; }
        .input-wrapper label { font-size: 13px; font-weight: 500; color: var(--text-muted); }
        .input-wrapper input { padding: 12px 16px; background: var(--bg); border: 1px solid var(--border); border-radius: 8px; color: var(--text-main); font-size: 14px; font-family: 'JetBrains Mono', monospace; transition: 0.2s; }
        .input-wrapper input:focus { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(99,102,241,0.2); }
        
        .result-box { display: flex; flex-direction: column; gap: 16px; }
        .data-card { background: var(--bg); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
        .data-header { background: var(--surface-hover); padding: 12px 16px; font-size: 13px; font-weight: 600; color: var(--text-main); display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); }
        .data-grid { display: grid; grid-template-columns: 1fr; gap: 1px; background: var(--border); }
        .data-item { background: var(--surface); padding: 12px 16px; display: flex; flex-direction: column; gap: 4px; }
        .data-label { font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; }
        .data-val { font-size: 14px; font-weight: 500; color: var(--text-main); font-family: 'JetBrains Mono', monospace; word-break: break-all; cursor: pointer; }
        .data-val:hover { color: var(--primary); }
        
        .loader-container { display: flex; align-items: center; justify-content: center; padding: 40px; flex-direction: column; gap: 16px; color: var(--text-muted); }
        .spinner { width: 32px; height: 32px; border: 3px solid var(--border); border-top-color: var(--primary); border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        
        .empty-state { text-align: center; padding: 40px; color: var(--text-muted); font-size: 14px; }

        .toast { position: fixed; bottom: 24px; right: 24px; background: var(--surface); border: 1px solid var(--border); padding: 12px 20px; border-radius: 8px; font-size: 14px; font-weight: 500; box-shadow: 0 10px 30px rgba(0,0,0,0.5); transform: translateY(150%); transition: 0.3s; z-index: 2000; display: flex; align-items: center; gap: 10px; }
        .toast.show { transform: translateY(0); }
        .toast.success { border-left: 4px solid var(--success); }
        .toast.error { border-left: 4px solid var(--danger); }

        @media (min-width: 992px) {
            .sidebar { position: static; transform: none; width: 260px; flex-shrink: 0; height: auto; border-right: 1px solid var(--border); }
            .hamburger { display: none; }
            .data-grid { grid-template-columns: 1fr 1fr; }
            .data-item.full { grid-column: span 2; }
        }
    </style>
</head>
<body>
    <div class="toast" id="toast">Bildirim</div>

    <div id="screen-auth" class="auth-wrapper">
        <div class="auth-card">
            <h1>ShopSphere</h1>
            <p>Gelişmiş OSINT & İstihbarat Paneli</p>
            <div id="form-login">
                <div class="form-group"><label>Kullanıcı Adı</label><input type="text" id="l_user" placeholder="kullanici_adi"></div>
                <div class="form-group"><label>Şifre</label><input type="password" id="l_pass" placeholder="••••••••"></div>
                <button class="btn" onclick="doLogin()">Giriş Yap</button>
                <div class="auth-switch" onclick="toggleAuth()">Hesabınız yok mu? <span>Kayıt Olun</span></div>
            </div>
            <div id="form-register" style="display:none;">
                <div class="form-group"><label>Kullanıcı Adı</label><input type="text" id="r_user" placeholder="yeni_kullanici"></div>
                <div class="form-group"><label>Şifre</label><input type="password" id="r_pass" placeholder="••••••••"></div>
                <button class="btn" onclick="doRegister()">Kayıt Ol</button>
                <div class="auth-switch" onclick="toggleAuth()">Zaten hesabınız var mı? <span>Giriş Yapın</span></div>
            </div>
        </div>
    </div>

    <div id="screen-app" class="app-layout" style="display:none;">
        <div class="sidebar-overlay" id="overlay" onclick="toggleMenu()"></div>
        <aside class="sidebar" id="sidebar">
            <div class="sidebar-header">
                <h2>ShopSphere</h2>
                <button class="logout-btn" onclick="doLogout()">Çıkış</button>
            </div>
            <div class="sidebar-nav">
                <div class="nav-title">Kişisel Sorgular</div>
                <div class="nav-item active" onclick="setForm('adsoyad', this)">👤 Ad Soyad</div>
                <div class="nav-item" onclick="setForm('aile', this)">👨‍👩‍👧‍👦 Aile Sorgu</div>
                <div class="nav-item" onclick="setForm('adres', this)">📍 Adres Sorgu</div>
                <div class="nav-item" onclick="setForm('tcgsm', this)">📱 TC → GSM</div>
                <div class="nav-item" onclick="setForm('gsmtc', this)">📞 GSM → TC</div>
                
                <div class="nav-title">OSINT Araçları</div>
                <div class="nav-item" onclick="setForm('osint_ip', this)">🌐 IP Sorgu</div>
                <div class="nav-item" onclick="setForm('osint_domain', this)">🔗 DNS Sorgu</div>
                <div class="nav-item" onclick="setForm('osint_whois', this)">🌍 WHOIS Sorgu</div>
                <div class="nav-item" onclick="setForm('osint_github', this)">🐙 GitHub Sorgu</div>
                <div class="nav-item" onclick="setForm('osint_mac', this)">📡 MAC Sorgu</div>
                <div class="nav-item" onclick="setForm('osint_url', this)">🕸️ URL Çözücü</div>
                <div class="nav-item" onclick="setForm('osint_cve', this)">🚨 CVE Zafiyet</div>
                <div class="nav-item" onclick="setForm('osint_hash', this)">🧬 Hash Oluştur</div>

                <div class="nav-title" style="margin-top:24px;">Kanallarımız</div>
                <a href="https://t.me/genelmerkezkanal" target="_blank" class="nav-item" style="color:#6366f1; text-decoration:none;">📢 Genel Merkez</a>
                <a href="https://t.me/markettchats" target="_blank" class="nav-item" style="color:#6366f1; text-decoration:none;">💬 Market Chat</a>
            </div>
        </aside>

        <main class="main-content">
            <header class="topbar">
                <div class="topbar-left">
                    <div class="hamburger" onclick="toggleMenu()"><span></span><span></span><span></span></div>
                    <span style="font-weight:600; font-size:14px; color:var(--text-muted);" id="bc-text"></span>
                </div>
                <div class="user-badge">
                    <span id="uname">Kullanıcı</span>
                </div>
            </header>

            <div class="content-area">
                <div class="card">
                    <div class="card-header">
                        <div class="card-title" id="qTitle">Ad Soyad Sorgu</div>
                    </div>
                    <div class="form-row" id="inputs"></div>
                    <button class="btn" id="submitBtn" onclick="runQuery()">Sorgula</button>
                </div>

                <div class="card">
                    <div class="card-header">
                        <div class="card-title">Sonuçlar</div>
                        <button class="logout-btn" onclick="copyAll()" id="copyBtn" style="display:none;">Kopyala</button>
                    </div>
                    <div id="output">
                        <div class="empty-state">Sorgu yapmak için formu doldurun.</div>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <script>
        function toast(msg, type='success') {
            let t = document.getElementById('toast');
            t.innerText = msg;
            t.className = 'toast show ' + type;
            setTimeout(() => t.className = 'toast', 3000);
        }

        function toggleAuth() {
            let l = document.getElementById('form-login'), r = document.getElementById('form-register');
            if(l.style.display === 'none') { l.style.display = 'block'; r.style.display = 'none'; }
            else { l.style.display = 'none'; r.style.display = 'block'; }
        }
        async function doLogin() {
            let u = document.getElementById('l_user').value, p = document.getElementById('l_pass').value;
            let res = await fetch('/api/login', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({username:u, password:p}) }).then(r=>r.json());
            if(res.success) { toast("Giriş başarılı!"); initApp(); }
            else toast(res.error, 'error');
        }
        async function doRegister() {
            let u = document.getElementById('r_user').value, p = document.getElementById('r_pass').value;
            let res = await fetch('/api/register', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({username:u, password:p}) }).then(r=>r.json());
            if(res.success) { toast("Kayıt başarılı, giriş yapın."); toggleAuth(); }
            else toast(res.error, 'error');
        }
        function doLogout() {
            fetch('/api/logout').then(() => location.reload());
        }

        async function initApp() {
            let auth = await fetch('/api/check_auth').then(r=>r.json());
            if(!auth.success) return;
            document.getElementById('screen-auth').style.display = 'none';
            document.getElementById('screen-app').style.display = 'flex';
            document.getElementById('uname').innerText = auth.username;
            
            setForm('adsoyad', document.querySelector('.nav-item'));
            
            setInterval(async () => {
                let r = await fetch('/api/get_broadcast').then(res=>res.json());
                if(r.success && r.broadcast) document.getElementById('bc-text').innerText = r.broadcast;
            }, 10000);
        }

        function toggleMenu() {
            document.getElementById('sidebar').classList.toggle('open');
            document.getElementById('overlay').classList.toggle('show');
        }

        let currentType = 'adsoyad';
        let lastData = null;

        const MENU = {
            "adsoyad": { title: "Ad Soyad Sorgu", fields: [{id:'ad', label:'Ad'}, {id:'soyad', label:'Soyad'}] },
            "aile": { title: "Aile Sorgu", fields: [{id:'tc', label:'TC Kimlik No', max:11}] },
            "adres": { title: "Adres Sorgu", fields: [{id:'tc', label:'TC Kimlik No', max:11}] },
            "tcgsm": { title: "TC → GSM", fields: [{id:'tc', label:'TC Kimlik No', max:11}] },
            "gsmtc": { title: "GSM → TC", fields: [{id:'gsm', label:'GSM Numarası'}] },
            
            "osint_ip": { title: "IP Adresi Sorgu", fields: [{id:'ip', label:'IP Adresi (8.8.8.8)'}] },
            "osint_domain": { title: "DNS Sorgu", fields: [{id:'domain', label:'Domain (google.com)'}] },
            "osint_whois": { title: "WHOIS Sorgu", fields: [{id:'domain', label:'Domain (google.com)'}] },
            "osint_github": { title: "GitHub Kullanıcı Sorgu", fields: [{id:'user', label:'Kullanıcı Adı'}] },
            "osint_mac": { title: "MAC Adresi Sorgu", fields: [{id:'mac', label:'MAC Adresi'}] },
            "osint_url": { title: "URL Çözücü", fields: [{id:'url', label:'Kısa Link'}] },
            "osint_cve": { title: "CVE Zafiyet Ara", fields: [{id:'keyword', label:'Yazılım (apache)'}] },
            "osint_hash": { title: "Hash Oluşturucu", fields: [{id:'text', label:'Metin'}] }
        };

        function setForm(type, el) {
            currentType = type;
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            if(el) el.classList.add('active');
            if(window.innerWidth < 992) toggleMenu();

            let def = MENU[type];
            document.getElementById('qTitle').innerText = def.title;
            let h = '';
            def.fields.forEach(f => h += `<div class="input-wrapper"><label>${f.label}</label><input type="text" id="${f.id}" ${f.max?`maxlength="${f.max}"`:''}></div>`);
            document.getElementById('inputs').innerHTML = h;
            document.getElementById('output').innerHTML = '<div class="empty-state">Sorgu bekleniyor...</div>';
            document.getElementById('copyBtn').style.display = 'none';
            lastData = null;
        }

        async function runQuery() {
            let def = MENU[currentType];
            let payload = { type: currentType };
            for(let f of def.fields) {
                let v = document.getElementById(f.id).value.trim();
                if(!v) return toast(f.label + " zorunludur.", "error");
                payload[f.id] = v;
            }

            let btn = document.getElementById('submitBtn');
            btn.disabled = true; btn.innerText = "Sorgulanıyor...";
            document.getElementById('output').innerHTML = '<div class="loader-container"><div class="spinner"></div><span>Sorgu işleniyor...</span></div>';

            try {
                let r = await fetch('/api/sorgu', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
                let data = await r.json();
                renderResult(data);
            } catch(err) {
                renderResult({success:false, error:"Sunucu hatası."});
            } finally {
                btn.disabled = false; btn.innerText = "Sorgula";
            }
        }

        function esc(s) { return String(s).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }
        function copyText(t) { navigator.clipboard.writeText(t).then(() => toast("Kopyalandı")); }

        function renderData(obj) {
            if(obj === null || obj === undefined || obj === '') return '<span style="color:#666">-</span>';
            if(typeof obj !== 'object') return `<span class="data-val" onclick="copyText('${esc(obj)}')">${esc(obj)}</span>`;
            
            if(Array.isArray(obj)) {
                if(obj.length === 0) return '<span style="color:#666">Veri yok</span>';
                return obj.map((i,idx) => `<div class="data-card" style="margin-top:10px;"><div class="data-header">Kayıt #${idx+1}</div><div class="data-grid">${renderData(i)}</div></div>`).join('');
            }
            
            let h = '';
            for(const [k,v] of Object.entries(obj)) {
                if(v === null || v === 'YOK' || v === 'NULL' || v === '') continue;
                let label = k.toUpperCase();
                
                if(typeof v === 'object') {
                    h += `<div class="data-item full"><span class="data-label">${label}</span>${renderData(v)}</div>`;
                } else {
                    let isFull = ['ADRES','KISI','BABA','ANNE','ES'].includes(label) ? 'full' : '';
                    h += `<div class="data-item ${isFull}"><span class="data-label">${label}</span><span class="data-val" onclick="copyText('${esc(v)}')">${esc(v)}</span></div>`;
                }
            }
            return h;
        }

        function renderResult(res) {
            let out = document.getElementById('output');
            if(!res.success) {
                out.innerHTML = `<div class="empty-state" style="color:var(--danger)">${esc(res.error)}</div>`;
                toast(res.error, 'error');
                return;
            }
            toast("Sorgu başarılı.");
            lastData = res.data;
            document.getElementById('copyBtn').style.display = 'block';

            let items = Array.isArray(res.data) ? res.data : [res.data];
            let h = '';
            items.forEach((item, i) => {
                if(!item || typeof item !== 'object') return;
                h += `<div class="data-card">
                        <div class="data-header">Kayıt #${i+1}</div>
                        <div class="data-grid">${renderData(item)}</div>
                      </div>`;
            });
            out.innerHTML = `<div class="result-box">${h}</div>` || '<div class="empty-state">Veri bulunamadı.</div>';
        }

        function copyAll() {
            if(!lastData) return;
            copyText(JSON.stringify(lastData, null, 2));
        }

        initApp();
    </script>
</body>
</html>
"""

ADMIN_DASHBOARD = r"""
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>Admin | ShopSphere</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root { --bg: #09090b; --surface: #18181b; --border: #27272a; --text: #f4f4f5; --text-muted: #a1a1aa; --primary: #6366f1; --danger: #ef4444; --success: #22c55e; }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
        body { background: var(--bg); color: var(--text); min-height: 100vh; padding: 30px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
        .header h1 { font-size: 24px; font-weight: 700; }
        .btn { padding: 8px 16px; background: var(--surface); border: 1px solid var(--border); color: var(--text); border-radius: 8px; text-decoration: none; font-size: 13px; font-weight: 500; cursor: pointer; transition: 0.2s; }
        .btn:hover { background: var(--surface-hover); }
        .btn-danger { color: var(--danger); border-color: var(--danger); }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
        .stat-card h3 { font-size: 13px; color: var(--text-muted); font-weight: 500; margin-bottom: 8px; }
        .stat-card p { font-size: 28px; font-weight: 700; color: var(--text); }
        .row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }
        .card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
        .card h3 { font-size: 15px; font-weight: 600; margin-bottom: 20px; }
        canvas { max-height: 250px; width: 100% !important; }
        .input-group { margin-bottom: 15px; }
        .input-group label { display: block; font-size: 13px; color: var(--text-muted); margin-bottom: 6px; }
        .input-group input { width: 100%; padding: 10px 14px; background: var(--bg); border: 1px solid var(--border); color: var(--text); border-radius: 8px; font-size: 14px; }
        .table-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
        table { width: 100%; border-collapse: collapse; text-align: left; font-size: 13px; }
        th, td { padding: 12px 16px; border-bottom: 1px solid var(--border); }
        th { background: var(--bg); color: var(--text-muted); font-weight: 500; }
        tr:hover { background: var(--surface-hover); }
        @media(max-width: 768px) { .row { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Yönetim Paneli</h1>
            <div>
                <a href="/gizli-cikis-narcissist" class="btn btn-danger">Çıkış</a>
                <a href="/" class="btn">Siteye Dön</a>
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card"><h3>Toplam Sorgu</h3><p>{{ total_queries }}</p></div>
            <div class="stat-card"><h3>Kayıtlı Kullanıcı</h3><p>{{ total_users }}</p></div>
            <div class="stat-card"><h3>Sistem Durumu</h3><p style="color:{{ 'var(--danger)' if maint == '1' else 'var(--success)' }}">{{ 'Bakımda' if maint == '1' else 'Aktif' }}</p></div>
            <div class="stat-card" style="display:flex; align-items:center;">
                <form action="/gizli-bakim-degistir" method="POST" style="width:100%;">
                    <button type="submit" class="btn" style="width:100%; background:{{ 'var(--success)' if maint == '1' else 'var(--danger)' }}; color:#fff; border:none; padding:12px;">
                        {{ 'Bakımı Kapat' if maint == '1' else 'Bakımı Aç' }}
                    </button>
                </form>
            </div>
        </div>

        <div class="row">
            <div class="card">
                <h3>Sorgu Dağılımı</h3>
                <canvas id="chartTypes"></canvas>
            </div>
            <div class="card">
                <h3>Canlı Duyuru</h3>
                <form action="/gizli-duyuru-gonder" method="POST">
                    <div class="input-group">
                        <label>Duyuru Metni</label>
                        <input type="text" name="bc_text" value="{{ current_bc }}" placeholder="Mesajınızı yazın...">
                    </div>
                    <button type="submit" class="btn" style="width:100%; border-color:var(--primary); color:var(--primary);">Yayınla</button>
                </form>
            </div>
        </div>

        <h3 style="margin-bottom:15px; font-size:16px;">Canlı Sorgu Akışı</h3>
        <div class="table-card">
            <table>
                <thead>
                    <tr><th>Tarih</th><th>Kullanıcı</th><th>Protokol</th><th>Parametre</th><th>IP Adresi</th><th>Durum</th></tr>
                </thead>
                <tbody>
                    {% for log in logs %}
                    <tr>
                        <td style="color:var(--text-muted)">{{ log[6] }}</td>
                        <td>{{ log[2] }}</td>
                        <td style="color:var(--primary)">{{ log[3] }}</td>
                        <td>{{ log[4] }}</td>
                        <td style="color:var(--text-muted)">{{ log[5] }}</td>
                        <td style="color:{{ 'var(--success)' if log[7]=='basarili' else 'var(--danger)' }}">{{ log[7]|upper }}</td>
                    </tr>
                    {% else %}
                    <tr><td colspan="6" style="text-align:center; padding:30px; color:var(--text-muted)">Kayıt yok.</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <script>
        new Chart(document.getElementById('chartTypes'), {
            type: 'doughnut',
            data: {
                labels: {{ chart_labels | safe }},
                datasets: [{
                    data: {{ chart_data | safe }},
                    backgroundColor: ['#6366f1', '#8b5cf6', '#ec4899', '#22c55e', '#eab308', '#a1a1aa'],
                    borderWidth: 0
                }]
            },
            options: { plugins: { legend: { labels: { color: '#f4f4f5', font: { family: 'Inter', size: 12 } } } }, cutout: '70%' }
        });
    </script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/register", methods=["POST"])
def api_register():
    req = request.json or {}
    u, p = req.get("username","").strip(), req.get("password","").strip()
    if len(u) < 3 or len(p) < 4: return jsonify({"success": False, "error": "Kullanıcı adı veya şifre kısa."})
    try:
        c = sqlite3.connect(DB_FILE)
        c.execute("INSERT INTO users (username, password, created_at) VALUES (?,?,?)", (u, generate_password_hash(p), datetime.now().strftime("%Y-%m-%d")))
        c.commit(); c.close()
        return jsonify({"success": True})
    except sqlite3.IntegrityError: return jsonify({"success": False, "error": "Bu kullanıcı adı alınmış."})
    except: return jsonify({"success": False, "error": "Sunucu hatası."})

@app.route("/api/login", methods=["POST"])
def api_login():
    req = request.json or {}
    u, p = req.get("username","").strip(), req.get("password","").strip()
    c = sqlite3.connect(DB_FILE)
    r = c.execute("SELECT id, username, password FROM users WHERE username=?", (u,)).fetchone()
    c.close()
    if r and check_password_hash(r[2], p):
        session['user_id'] = r[0]; session['username'] = r[1]
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Hatalı giriş."})

@app.route("/api/logout")
def api_logout():
    session.clear()
    return jsonify({"success": True})

@app.route("/api/check_auth")
def api_check_auth():
    if 'user_id' in session: return jsonify({"success": True, "username": session['username']})
    return jsonify({"success": False})

@app.route("/api/get_broadcast")
def api_get_broadcast():
    return jsonify({"success": True, "broadcast": get_setting("broadcast")})

@app.route("/api/sorgu", methods=["POST"])
def api_sorgu():
    if get_setting("maintenance") == "1": return jsonify({"success": False, "error": "Sistem bakımda."})
    if 'user_id' not in session: return jsonify({"success": False, "error": "Giriş yapmalısınız."})

    req = request.json or {}
    q_type = req.get("type")
    uid, uname, ip = session['user_id'], session['username'], request.remote_addr

    if q_type == "osint_ip":
        try: return jsonify({"success": True, "data": requests.get(f"http://ip-api.com/json/{req.get('ip')}", timeout=10).json()})
        except: return jsonify({"success": False, "error": "Sunucu hatası."})
    elif q_type == "osint_domain":
        try: return jsonify({"success": True, "data": requests.get(f"https://dns.google/resolve?name={req.get('domain')}&type=A", timeout=10).json()})
        except: return jsonify({"success": False, "error": "DNS hatası."})
    elif q_type == "osint_whois":
        try:
            r = requests.get(f"https://rdap.org/domain/{req.get('domain')}", timeout=10).json()
            return jsonify({"success": True, "data": {"Domain": r.get("ldhName"), "Status": r.get("status"), "Events": [e.get("eventAction") for e in r.get("events", [])]}})
        except: return jsonify({"success": False, "error": "WHOIS hatası."})
    elif q_type == "osint_mac":
        try: return jsonify({"success": True, "data": {"MAC": req.get('mac'), "Uretici": requests.get(f"https://api.macvendors.com/{req.get('mac')}", timeout=10).text}})
        except: return jsonify({"success": False, "error": "MAC hatası."})
    elif q_type == "osint_github":
        try:
            r = requests.get(f"https://api.github.com/users/{req.get('user')}", timeout=10).json()
            if r.get('message') == 'Not Found': return jsonify({"success": False, "error": "Kullanıcı yok."})
            return jsonify({"success": True, "data": r})
        except: return jsonify({"success": False, "error": "API hatası."})
    elif q_type == "osint_url":
        try: return jsonify({"success": True, "data": {"Asıl_Link": requests.get(f"https://unshorten.me/api/v2/unshorten?url={req.get('url')}", timeout=10).json().get("resolved_url")}})
        except: return jsonify({"success": False, "error": "Link çözülemedi."})
    elif q_type == "osint_cve":
        try:
            r = requests.get(f"https://cve.circl.lu/api/last", timeout=10).json()
            kw = req.get('keyword').lower()
            return jsonify({"success": True, "data": [{"ID": c.get('id'), "Özet": c.get('summary')} for c in r if kw in c.get('summary', '').lower()][:10]})
        except: return jsonify({"success": False, "error": "CVE hatası."})
    elif q_type == "osint_hash":
        try:
            txt = req.get('text').encode()
            return jsonify({"success": True, "data": {"MD5": hashlib.md5(txt).hexdigest(), "SHA1": hashlib.sha1(txt).hexdigest(), "SHA256": hashlib.sha256(txt).hexdigest()}})
        except: return jsonify({"success": False, "error": "Hash hatası."})

    API_MAP = {
        "adsoyad": {"url": f"{API_BASE}/adsoyadapi.php", "params": {"ad":"ad","soyad":"soyad"}},
        "aile": {"url": f"{API_BASE}/ailesorguapi.php", "params": {"tc":"tc"}},
        "adres": {"url": f"{API_BASE}/adrespro.php", "params": {"tc":"tc"}},
        "tcgsm": {"url": f"{API_BASE}/gsmpro.php", "params": {"tc":"tc"}},
        "gsmtc": {"url": f"{API_BASE}/gsmpro.php", "params": {"gsm":"gsm"}},
    }
    if q_type in API_MAP:
        api_info = API_MAP[q_type]
        params = {}; query_str = ""
        for k, rk in api_info["params"].items():
            val = req.get(k)
            if val: params[rk] = val; query_str += f"{val} "
        if not params: return jsonify({"success": False, "error": "Eksik parametre."})

        try:
            r = requests.get(api_info["url"], params=params, timeout=20, verify=False, headers={"User-Agent":"Mozilla/5.0"})
            data = r.json()
            is_ok = data.get("success") in [True, "true"] or data.get("durum") in ["basarili", "başarılı"] or data.get("status") == "success"
            result = data.get("data") or data.get("veri") or data.get("result")
            if not result and not is_ok:
                log_query(uid, uname, q_type, query_str, ip, "basarisiz")
                return jsonify({"success": False, "error": data.get("message") or "Bulunamadı."})
            log_query(uid, uname, q_type, query_str, ip, "basarili")
            return jsonify({"success": True, "data": result or data})
        except:
            log_query(uid, uname, q_type, query_str, ip, "hata")
            return jsonify({"success": False, "error": "API Sunucu Hatası."})

    return jsonify({"success": False, "error": "Geçersiz sorgu."})

@app.route("/gizli-admin-narcissist", methods=["GET", "POST"])
def secret_login():
    if request.method == "POST":
        if request.form.get("pass") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect("/gizli-dashboard-narcissist")
        return "Hatalı Şifre"
    return """
    <body style="background:#09090b;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;">
        <form method="POST" style="background:#18181b;padding:40px;border-radius:12px;text-align:center;border:1px solid #27272a;">
            <h2 style="margin-bottom:20px;">Admin Girişi</h2>
            <input type="password" name="pass" placeholder="Şifre" style="padding:12px;border-radius:8px;border:1px solid #27272a;background:#09090b;color:#fff;width:100%;margin-bottom:15px;">
            <button type="submit" style="padding:12px;background:#6366f1;color:#fff;border:none;border-radius:8px;width:100%;font-weight:bold;cursor:pointer;">Giriş</button>
        </form>
    </body>
    """

@app.route("/gizli-dashboard-narcissist")
def admin_dashboard():
    if not session.get("admin"): return redirect("/gizli-admin-narcissist")
    c = sqlite3.connect(DB_FILE)
    logs = c.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 50").fetchall()
    total_queries = c.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
    total_users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    q_stats = c.execute("SELECT query_type, COUNT(*) FROM logs GROUP BY query_type").fetchall()
    chart_labels = json.dumps([q[0] for q in q_stats])
    chart_data = json.dumps([q[1] for q in q_stats])
    c.close()
    return render_template_string(ADMIN_DASHBOARD, logs=logs, total_queries=total_queries, 
                                  total_users=total_users, maint=get_setting("maintenance"), 
                                  current_bc=get_setting("broadcast"),
                                  chart_labels=chart_labels, chart_data=chart_data)

@app.route("/gizli-bakim-degistir", methods=["POST"])
def admin_toggle_maint():
    if not session.get("admin"): return redirect("/")
    set_setting("maintenance", "0" if get_setting("maintenance") == "1" else "1")
    return redirect("/gizli-dashboard-narcissist")

@app.route("/gizli-duyuru-gonder", methods=["POST"])
def admin_broadcast():
    if not session.get("admin"): return redirect("/")
    set_setting("broadcast", request.form.get("bc_text", "").strip())
    return redirect("/gizli-dashboard-narcissist")

@app.route("/gizli-cikis-narcissist")
def admin_logout():
    session.pop("admin", None)
    return redirect("/")

# BURAYI RENDER İÇİN EKLEDİK:
if __name__ == "__main__":
    app.run()