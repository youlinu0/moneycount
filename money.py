#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""簡單的本機網頁記帳工具。只使用 Python 標準函式庫。"""

from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
from urllib.parse import urlparse

HOST = "127.0.0.1"
PORT = 8000
DB_PATH = Path(__file__).with_name("moneycount.db")

PAGE = r"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>記帳日常</title>
<style>
:root{font-family:system-ui,-apple-system,"Noto Sans TC",sans-serif;color:#25352d;background:#f4f6f2}
*{box-sizing:border-box}body{margin:0}.wrap{max-width:980px;margin:auto;padding:32px 20px 60px}
header{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:24px}
h1{font-size:26px;margin:0}header p{color:#748078;margin:5px 0 0;font-size:14px}
.month{display:flex;align-items:center;gap:12px;background:white;border:1px solid #e2e8e1;border-radius:14px;padding:8px}
.month button,.delete{border:0;background:#edf3ee;color:#315943;border-radius:9px;padding:9px 12px;cursor:pointer}
#monthLabel{font-weight:700;min-width:90px;text-align:center}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:18px}
.card,section{background:white;border:1px solid #e3e9e2;border-radius:16px;padding:18px}
.card span{display:block;color:#77837b;font-size:13px;margin-bottom:7px}.card strong{font-size:24px}
.income{color:#36805a}.expense{color:#bd6251}.balance{color:#315943}
section{margin-top:16px}h2{font-size:17px;margin:0 0 15px}
form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
label{font-size:13px;color:#637168;display:grid;gap:6px}
input,select{width:100%;padding:11px;border:1px solid #dce4dc;border-radius:9px;background:white;font:inherit;color:#25352d}
.wide{grid-column:1/-1}.submit{border:0;border-radius:10px;padding:12px;background:#315943;color:white;font:inherit;font-weight:700;cursor:pointer}
#message{min-height:20px;color:#bd6251;font-size:13px}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:12px 8px;border-bottom:1px solid #edf0ec;font-size:14px}th{color:#7b877e;font-size:12px}
.amount{text-align:right;white-space:nowrap}.delete{padding:7px 10px}.empty{text-align:center;padding:30px;color:#89948c}
@media(max-width:620px){.wrap{padding:22px 14px 40px}header{align-items:flex-start;flex-direction:column}.cards{gap:7px}.card{padding:13px 10px}.card strong{font-size:19px}form{grid-template-columns:1fr}.wide{grid-column:auto}table th:nth-child(4),table td:nth-child(4){display:none}th,td{padding:10px 5px;font-size:12px}}
</style>
</head>
<body><main class="wrap">
<header><div><h1>記帳日常</h1><p>簡單記下每一筆收支</p></div>
<div class="month"><button id="prev" aria-label="上個月">‹</button><span id="monthLabel"></span><button id="next" aria-label="下個月">›</button></div></header>
<div class="cards"><div class="card"><span>本月收入</span><strong class="income" id="incomeTotal">0</strong></div><div class="card"><span>本月支出</span><strong class="expense" id="expenseTotal">0</strong></div><div class="card"><span>本月結餘</span><strong class="balance" id="balanceTotal">0</strong></div></div>
<section><h2>新增一筆</h2><form id="entryForm">
<label>類型<select id="kind"><option value="expense">支出</option><option value="income">收入</option></select></label>
<label>金額（數字）<input id="amount" type="number" min="1" step="1" required placeholder="例如 120"></label>
<label>分類<select id="category"></select></label>
<label>日期<input id="entryDate" type="date" required></label>
<label class="wide">備註（選填）<input id="note" maxlength="120" placeholder="例如 午餐、薪水"></label>
<button class="submit wide" type="submit">加入記錄</button><div class="wide" id="message"></div>
</form></section>
<section><h2>收支紀錄</h2><div style="overflow-x:auto"><table><thead><tr><th>日期</th><th>類型</th><th>分類</th><th>備註</th><th class="amount">金額</th><th></th></tr></thead><tbody id="rows"></tbody></table></div></section>
</main>
<script>
var selectedMonth = new Date(); selectedMonth.setDate(1);
var categoryMap = {expense:["飲食","交通","生活","購物","娛樂","其他"],income:["薪水","獎金","禮金","其他"]};
function pad(n){return String(n).padStart(2,"0")}
function monthKey(){return selectedMonth.getFullYear()+"-"+pad(selectedMonth.getMonth()+1)}
function money(n){return Number(n).toLocaleString("zh-TW")}
function updateCategories(){var kind=document.getElementById("kind").value;document.getElementById("category").innerHTML=categoryMap[kind].map(function(x){return "<option>"+x+"</option>"}).join("")}
async function loadEntries(){
 document.getElementById("monthLabel").textContent=selectedMonth.getFullYear()+" 年 "+(selectedMonth.getMonth()+1)+" 月";
 var response=await fetch("/api/entries?month="+monthKey());var data=await response.json();
 document.getElementById("incomeTotal").textContent=money(data.income);
 document.getElementById("expenseTotal").textContent=money(data.expense);
 document.getElementById("balanceTotal").textContent=money(data.income-data.expense);
 var tbody=document.getElementById("rows");
 if(!data.entries.length){tbody.innerHTML='<tr><td colspan="6" class="empty">這個月還沒有記錄</td></tr>';return}
 tbody.innerHTML=data.entries.map(function(e){return "<tr><td>"+e.date+"</td><td>"+(e.kind==="income"?"收入":"支出")+"</td><td>"+escapeHtml(e.category)+"</td><td>"+escapeHtml(e.note||"—")+"</td><td class='amount "+(e.kind==="income"?"income":"expense")+"'>"+(e.kind==="income"?"+":"−")+money(e.amount)+"</td><td><button class='delete' data-id='"+e.id+"'>刪除</button></td></tr>"}).join("");
}
function escapeHtml(s){return String(s).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]})}
document.getElementById("kind").addEventListener("change",updateCategories);
document.getElementById("prev").onclick=function(){selectedMonth.setMonth(selectedMonth.getMonth()-1);loadEntries()};
document.getElementById("next").onclick=function(){selectedMonth.setMonth(selectedMonth.getMonth()+1);loadEntries()};
document.getElementById("entryDate").value=new Date().toISOString().slice(0,10);
document.getElementById("entryForm").addEventListener("submit",async function(ev){
 ev.preventDefault();var message=document.getElementById("message");message.textContent="";
 var payload={kind:document.getElementById("kind").value,amount:Number(document.getElementById("amount").value),category:document.getElementById("category").value,date:document.getElementById("entryDate").value,note:document.getElementById("note").value.trim()};
 var response=await fetch("/api/entries",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
 var result=await response.json();if(!response.ok){message.textContent=result.error||"無法新增記錄";return}
 this.reset();document.getElementById("entryDate").value=new Date().toISOString().slice(0,10);updateCategories();loadEntries();
});
document.getElementById("rows").addEventListener("click",async function(ev){
 var id=ev.target.getAttribute("data-id");if(!id)return;
 await fetch("/api/entries/"+id,{method:"DELETE"});loadEntries();
});
updateCategories();loadEntries();
</script></body></html>"""

def connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def initialize():
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL CHECK(kind IN ('income','expense')),
            amount INTEGER NOT NULL CHECK(amount > 0),
            category TEXT NOT NULL,
            entry_date TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT ''
        )""")

class Handler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path)
        if path.path == "/":
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path.path == "/api/entries":
            month = path.query.removeprefix("month=")[:7]
            if len(month) != 7 or month[4] != "-":
                return self.send_json({"error": "月份格式錯誤"}, 400)
            with connect() as db:
                rows = db.execute(
                    "SELECT id, kind, amount, category, entry_date, note FROM entries "
                    "WHERE substr(entry_date,1,7)=? ORDER BY entry_date DESC, id DESC", (month,)
                ).fetchall()
                income = sum(r["amount"] for r in rows if r["kind"] == "income")
                expense = sum(r["amount"] for r in rows if r["kind"] == "expense")
            entries = [{"id": r["id"], "kind": r["kind"], "amount": r["amount"],
                        "category": r["category"], "date": r["entry_date"], "note": r["note"]}
                       for r in rows]
            self.send_json({"entries": entries, "income": income, "expense": expense})
        else:
            self.send_json({"error": "找不到頁面"}, 404)

    def do_POST(self):
        if self.path != "/api/entries":
            return self.send_json({"error": "找不到頁面"}, 404)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length))
            kind = data.get("kind")
            amount = data.get("amount")
            category = str(data.get("category", "")).strip()[:40]
            entry_date = str(data.get("date", ""))
            note = str(data.get("note", "")).strip()[:120]
            if kind not in ("income", "expense") or not isinstance(amount, int) or amount <= 0:
                raise ValueError("請輸入大於 0 的整數金額")
            if not category:
                raise ValueError("請選擇分類")
            date.fromisoformat(entry_date)
            with connect() as db:
                db.execute("INSERT INTO entries(kind,amount,category,entry_date,note) VALUES(?,?,?,?,?)",
                           (kind, amount, category, entry_date, note))
            self.send_json({"ok": True}, 201)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self.send_json({"error": str(exc) or "資料格式錯誤"}, 400)

    def do_DELETE(self):
        parts = self.path.split("/")
        if len(parts) != 4 or parts[1:3] != ["api", "entries"] or not parts[3].isdigit():
            return self.send_json({"error": "找不到記錄"}, 404)
        with connect() as db:
            cursor = db.execute("DELETE FROM entries WHERE id=?", (int(parts[3]),))
        self.send_json({"ok": True} if cursor.rowcount else {"error": "找不到記錄"},
                       200 if cursor.rowcount else 404)

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))

if __name__ == "__main__":
    initialize()
    print("記帳日常已啟動：http://127.0.0.1:%s" % PORT)
    print("資料庫位置：%s" % DB_PATH)
    try:
        ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\n已停止記帳日常。")
