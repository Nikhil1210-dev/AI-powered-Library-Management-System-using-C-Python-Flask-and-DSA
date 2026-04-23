

import os, subprocess
import mysql.connector
from datetime import datetime, date, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import bcrypt
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
except Exception:
    pass

app = Flask(__name__,
            template_folder='../frontend/templates',
            static_folder='../frontend/static')
app.secret_key = os.environ.get('SECRET_KEY', 'librarypro-secret-2024')

DB_CFG = {
    'host':     os.environ.get('MYSQL_HOST',     'localhost'),
    'user':     os.environ.get('MYSQL_USER',     'root'),
    'password': os.environ.get('MYSQL_PASSWORD', ''),
    'database': os.environ.get('MYSQL_DB',       'librarypro'),
}

def get_db():
    return mysql.connector.connect(**DB_CFG)

_base   = os.path.dirname(os.path.abspath(__file__))
CPP_BIN = os.path.join(_base, 'library.exe' if os.name == 'nt' else 'library')
FINE_PER_DAY = 2.00
LOAN_DAYS    = 14

def run_cpp(args):
    try:
        r = subprocess.run([CPP_BIN]+args, capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except Exception as e:
        return f'ERROR:{e}'

def login_required(f):
    @wraps(f)
    def dec(*a,**k):
        if 'user_id' not in session:
            flash('Please log in first.','warning')
            return redirect(url_for('login'))
        return f(*a,**k)
    return dec

def admin_required(f):
    @wraps(f)
    def dec(*a,**k):
        if 'user_id' not in session: return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Admin access required.','danger')
            return redirect(url_for('dashboard'))
        return f(*a,**k)
    return dec

def get_notifs(uid):
    try:
        c=get_db(); cur=c.cursor(dictionary=True)
        cur.execute("SELECT * FROM notifications WHERE user_id=%s AND is_read=0 ORDER BY created_at DESC LIMIT 10",(uid,))
        r=cur.fetchall(); cur.close(); c.close(); return r
    except: return []

def add_notif(uid,msg):
    try:
        c=get_db(); cur=c.cursor()
        cur.execute("INSERT INTO notifications(user_id,message) VALUES(%s,%s)",(uid,msg))
        c.commit(); cur.close(); c.close()
    except: pass

def calc_fine(due):
    if not due: return 0.0
    if isinstance(due,str):
        try: due=datetime.strptime(due,'%Y-%m-%d').date()
        except: return 0.0
    d=(date.today()-due).days
    return round(d*FINE_PER_DAY,2) if d>0 else 0.0

def parse_book(line):
    p=line.split('|')
    if len(p)<9: return None
    return {'id':int(p[0]),'title':p[1],'author':p[2],'category':p[3],
            'issued':int(p[4]),'student_name':p[5],'student_id':p[6],
            'due_date':p[7],'vip':int(p[8]),
            'fine':calc_fine(p[7]) if p[4]=='1' else 0.0}

@app.route('/')
def index():
    return redirect(url_for('dashboard' if 'user_id' in session else 'login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=request.form.get('username','').strip()
        p=request.form.get('password','').strip()
        try:
            conn=get_db(); cur=conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM users WHERE username=%s",(u,))
            user=cur.fetchone(); cur.close(); conn.close()
            if user and bcrypt.checkpw(p.encode(),user['password_hash'].encode()):
                for k in ('user_id','username','full_name','role','is_vip'):
                    session[k]=user['id' if k=='user_id' else k]
                flash(f"Welcome back, {user['full_name']}! 👋",'success')
                return redirect(url_for('dashboard'))
            flash('Invalid username or password.','danger')
        except Exception as e:
            flash(f'DB error: {e}','danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear(); flash('Logged out.','info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        fn=request.form.get('full_name','').strip()
        un=request.form.get('username','').strip()
        em=request.form.get('email','').strip()
        pw=request.form.get('password','').strip()
        vip=1 if request.form.get('is_vip') else 0
        ph=bcrypt.hashpw(pw.encode(),bcrypt.gensalt()).decode()
        try:
            conn=get_db(); cur=conn.cursor()
            cur.execute("INSERT INTO users(username,password_hash,role,full_name,email,is_vip) VALUES(%s,%s,'student',%s,%s,%s)",
                        (un,ph,fn,em,vip))
            conn.commit(); cur.close(); conn.close()
            flash('Account created! Log in.','success')
            return redirect(url_for('login'))
        except: flash('Username/email already exists.','danger')
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    raw=run_cpp(['display'])
    books=[parse_book(l) for l in raw.splitlines() if parse_book(l)]
    total=len(books); issued=sum(1 for b in books if b['issued']); avail=total-issued
    qr=run_cpp(['queue']); qc=0 if qr in ('','EMPTY') else len(qr.splitlines())
    try:
        conn=get_db(); cur=conn.cursor(dictionary=True)
        cur.execute("""SELECT t.*,b.title AS book_title,u.full_name AS student_name
            FROM transactions t JOIN books b ON t.book_id=b.id JOIN users u ON t.user_id=u.id
            ORDER BY t.issue_date DESC LIMIT 5""")
        rtx=cur.fetchall(); cur.close(); conn.close()
    except: rtx=[]
    return render_template('dashboard.html',books=books,total=total,issued=issued,
        available=avail,queue_count=qc,notifications=get_notifs(session['user_id']),recent_tx=rtx)

@app.route('/books')
@login_required
def books():
    q=request.args.get('q','').strip(); cat=request.args.get('category','').strip()
    page=int(request.args.get('page',1)); per=10
    raw=run_cpp(['search',q]) if q else run_cpp(['display'])
    all_b=[parse_book(l) for l in raw.splitlines() if parse_book(l) and l!='NONE']
    if cat: all_b=[b for b in all_b if b['category']==cat]
    tot=len(all_b); tp=max(1,(tot+per-1)//per); page=max(1,min(page,tp))
    paged=all_b[(page-1)*per:page*per]
    cats=sorted(set(b['category'] for b in all_b))
    return render_template('books.html',books=paged,total=tot,page=page,total_pages=tp,
        search=q,cat=cat,categories=cats,notifications=get_notifs(session['user_id']))

@app.route('/add_book',methods=['POST'])
@admin_required
def add_book():
    bid=request.form.get('book_id','').strip(); title=request.form.get('title','').strip()
    auth=request.form.get('author','').strip(); cat=request.form.get('category','General').strip()
    if not all([bid,title,auth]): flash('All fields required.','danger'); return redirect(url_for('books'))
    try:
        conn=get_db(); cur=conn.cursor()
        cur.execute("INSERT INTO books(id,title,author,category) VALUES(%s,%s,%s,%s)",(bid,title,auth,cat))
        conn.commit(); cur.close(); conn.close()
    except Exception as e: flash(f'DB: {e}','danger'); return redirect(url_for('books'))
    run_cpp(['add',bid,title,auth,cat])
    flash(f'Book "{title}" added! 📚','success'); return redirect(url_for('books'))

@app.route('/delete_book',methods=['POST'])
@admin_required
def delete_book():
    bid=request.form.get('book_id','').strip(); run_cpp(['delete',bid])
    try:
        conn=get_db(); cur=conn.cursor()
        cur.execute("DELETE FROM books WHERE id=%s",(bid,)); conn.commit(); cur.close(); conn.close()
    except Exception as e: flash(f'DB: {e}','danger'); return redirect(url_for('books'))
    flash('Book deleted.','success'); return redirect(url_for('books'))

@app.route('/issue',methods=['GET','POST'])
@login_required
def issue_book():
    notifs=get_notifs(session['user_id'])
    if request.method=='POST':
        bid=request.form.get('book_id','').strip()
        sn=request.form.get('student_name','').strip()
        si=request.form.get('student_id','').strip()
        vip=1 if request.form.get('vip') else 0
        idate=date.today(); ddate=idate+timedelta(days=LOAN_DAYS)
        result=run_cpp(['issue',bid,sn,si,str(ddate),str(vip)])
        try:
            conn=get_db(); cur=conn.cursor(dictionary=True)
            cur.execute("SELECT id FROM users WHERE username=%s",(si,))
            ur=cur.fetchone(); uid=ur['id'] if ur else session['user_id']
            cur2=conn.cursor()
            if 'ISSUED' in result:
                cur2.execute("INSERT INTO transactions(book_id,user_id,issue_date,due_date,status) VALUES(%s,%s,%s,%s,'active')",
                             (bid,uid,idate,ddate))
                cur2.execute("UPDATE books SET available=available-1 WHERE id=%s AND available>0",(bid,))
                conn.commit(); flash(f'✅ Issued! Due: {ddate}','success')
            elif 'QUEUED' in result:
                cur2.execute("INSERT INTO queue(book_id,user_id,priority) VALUES(%s,%s,%s)",
                             (bid,uid,1 if vip else 2))
                conn.commit(); flash('📋 Added to waiting queue!','info')
            else: flash(f'Result: {result}','warning')
            cur.close(); conn.close()
        except Exception as e: flash(f'Error: {e}','danger')
        return redirect(url_for('issue_book'))
    raw=run_cpp(['display']); bks=[parse_book(l) for l in raw.splitlines() if parse_book(l)]
    return render_template('issue.html',books=bks,notifications=notifs)

@app.route('/return',methods=['GET','POST'])
@login_required
def return_book():
    notifs=get_notifs(session['user_id'])
    if request.method=='POST':
        bid=request.form.get('book_id','').strip(); rdate=str(date.today())
        run_cpp(['return',bid,rdate])
        try:
            conn=get_db(); cur=conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM transactions WHERE book_id=%s AND status='active' ORDER BY issue_date DESC LIMIT 1",(bid,))
            tx=cur.fetchone()
            if tx:
                fine=calc_fine(tx['due_date']); cur2=conn.cursor()
                cur2.execute("UPDATE transactions SET return_date=%s,status='returned',fine_amount=%s WHERE id=%s",
                             (rdate,fine,tx['id']))
                cur2.execute("UPDATE books SET available=available+1 WHERE id=%s",(bid,))
                conn.commit()
                flash(f'✅ Returned!'+(f' Fine: ₹{fine:.2f}' if fine>0 else ''),
                      'success' if fine==0 else 'warning')
            else: flash('Book returned.','info')
            cur.close(); conn.close()
        except Exception as e: flash(f'Error: {e}','danger')
        return redirect(url_for('return_book'))
    raw=run_cpp(['display'])
    bks=[parse_book(l) for l in raw.splitlines() if parse_book(l) and parse_book(l)['issued']==1]
    return render_template('return.html',books=bks,notifications=notifs)

@app.route('/queue')
@login_required
def queue_page():
    raw=run_cpp(['queue']); entries=[]
    if raw not in ('','EMPTY'):
        for line in raw.splitlines():
            p=line.split('|')
            if len(p)>=4: entries.append({'book_id':p[0],'student':p[1],'sid':p[2],'type':p[3]})
    return render_template('queue.html',entries=entries,notifications=get_notifs(session['user_id']))

@app.route('/stack')
@login_required
def stack_page():
    raw=run_cpp(['stack']); entries=[]
    if raw not in ('','EMPTY'):
        for line in raw.splitlines():
            p=line.split('|')
            if len(p)>=2: entries.append({'book_id':p[0],'title':p[1]})
    return render_template('stack.html',entries=entries,notifications=get_notifs(session['user_id']))

@app.route('/recommend/<int:book_id>')
@login_required
def recommend(book_id):
    raw=run_cpp(['recommend',str(book_id),'6']); recs=[]
    if raw!='NONE':
        for line in raw.splitlines():
            p=line.split('|')
            if len(p)>=4: recs.append({'id':p[0],'title':p[1],'author':p[2],'category':p[3]})
    return jsonify(recs)

@app.route('/analytics')
@admin_required
def analytics():
    try:
        conn=get_db(); cur=conn.cursor(dictionary=True)
        cur.execute("SELECT DATE(issue_date) AS day,COUNT(*) AS cnt FROM transactions WHERE issue_date>=DATE_SUB(CURDATE(),INTERVAL 14 DAY) GROUP BY day ORDER BY day")
        di=cur.fetchall()
        cur.execute("SELECT b.title,COUNT(t.id) AS cnt FROM transactions t JOIN books b ON t.book_id=b.id GROUP BY b.title ORDER BY cnt DESC LIMIT 8")
        pop=cur.fetchall()
        cur.execute("SELECT u.full_name,COUNT(t.id) AS cnt FROM transactions t JOIN users u ON t.user_id=u.id WHERE t.status='active' GROUP BY u.full_name ORDER BY cnt DESC LIMIT 8")
        au=cur.fetchall()
        cur.execute("SELECT category,COUNT(*) AS cnt FROM books GROUP BY category ORDER BY cnt DESC")
        cats=cur.fetchall()
        cur.execute("SELECT t.*,b.title,u.full_name,DATEDIFF(CURDATE(),t.due_date) AS days_late FROM transactions t JOIN books b ON t.book_id=b.id JOIN users u ON t.user_id=u.id WHERE t.status='active' AND t.due_date<CURDATE() ORDER BY days_late DESC")
        ov=cur.fetchall(); cur.close(); conn.close()
    except: di=pop=au=cats=ov=[]
    stats={}
    for line in run_cpp(['stats']).splitlines():
        if ':' in line: k,v=line.split(':',1); stats[k]=v
    return render_template('analytics.html',daily_issues=di,popular=pop,active_users=au,
        categories=cats,overdue=ov,stats=stats,notifications=get_notifs(session['user_id']))

@app.route('/students')
@admin_required
def students():
    try:
        conn=get_db(); cur=conn.cursor(dictionary=True)
        cur.execute("""SELECT u.*,COUNT(t.id) AS total_borrowed,
            SUM(CASE WHEN t.status='active' THEN 1 ELSE 0 END) AS currently_borrowed,
            COALESCE(SUM(t.fine_amount),0) AS total_fines
            FROM users u LEFT JOIN transactions t ON u.id=t.user_id
            WHERE u.role='student' GROUP BY u.id ORDER BY u.full_name""")
        sd=cur.fetchall(); cur.close(); conn.close()
    except: sd=[]
    return render_template('students.html',students=sd,notifications=get_notifs(session['user_id']))

@app.route('/transactions')
@admin_required
def transactions():
    page=int(request.args.get('page',1)); per=15; off=(page-1)*per
    try:
        conn=get_db(); cur=conn.cursor(dictionary=True)
        cur.execute("SELECT COUNT(*) AS c FROM transactions"); tot=cur.fetchone()['c']
        cur.execute("""SELECT t.*,b.title AS book_title,u.full_name AS student_name,
            DATEDIFF(CURDATE(),t.due_date) AS days_late
            FROM transactions t JOIN books b ON t.book_id=b.id JOIN users u ON t.user_id=u.id
            ORDER BY t.issue_date DESC LIMIT %s OFFSET %s""",(per,off))
        txs=cur.fetchall(); cur.close(); conn.close()
    except: txs=tot=0
    tp=max(1,(tot+per-1)//per) if tot else 1
    return render_template('transactions.html',transactions=txs,page=page,total_pages=tp,
        notifications=get_notifs(session['user_id']))

@app.route('/profile')
@login_required
def profile():
    try:
        conn=get_db(); cur=conn.cursor(dictionary=True)
        cur.execute("SELECT t.*,b.title AS book_title FROM transactions t JOIN books b ON t.book_id=b.id WHERE t.user_id=%s ORDER BY t.issue_date DESC",(session['user_id'],))
        mb=cur.fetchall(); cur.close(); conn.close()
    except: mb=[]
    tf=sum(calc_fine(t['due_date']) for t in mb if t['status']=='active')
    return render_template('profile.html',my_books=mb,total_fine=tf,notifications=get_notifs(session['user_id']))

@app.route('/notifications/mark_read',methods=['POST'])
@login_required
def mark_notifications_read():
    try:
        conn=get_db(); cur=conn.cursor()
        cur.execute("UPDATE notifications SET is_read=1 WHERE user_id=%s",(session['user_id'],))
        conn.commit(); cur.close(); conn.close()
    except: pass
    return jsonify({'status':'ok'})

@app.route('/api/stats')
@login_required
def api_stats():
    try:
        conn=get_db(); cur=conn.cursor(dictionary=True)
        cur.execute("SELECT DATE(issue_date) AS day,COUNT(*) AS cnt FROM transactions WHERE issue_date>=DATE_SUB(CURDATE(),INTERVAL 7 DAY) GROUP BY day ORDER BY day")
        daily=cur.fetchall()
        cur.execute("SELECT b.category,COUNT(*) AS cnt FROM transactions t JOIN books b ON t.book_id=b.id GROUP BY b.category")
        cats=cur.fetchall()
        cur.execute("SELECT COUNT(*) AS c FROM transactions WHERE status='active'"); active=cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) AS c FROM transactions WHERE status='active' AND due_date<CURDATE()"); ov=cur.fetchone()['c']
        cur.close(); conn.close()
        return jsonify({'daily':[{'day':str(r['day']),'cnt':r['cnt']} for r in daily],
            'cats':[{'cat':r['category'],'cnt':r['cnt']} for r in cats],'active':active,'overdue':ov})
    except Exception as e:
        return jsonify({'error':str(e),'daily':[],'cats':[],'active':0,'overdue':0})

@app.errorhandler(404)
def not_found(e): return render_template('error.html',code=404,msg="Page not found."),404

@app.errorhandler(500)
def server_error(e): return render_template('error.html',code=500,msg="Server error."),500

@app.context_processor
def inject_globals():
    nc=0
    if 'user_id' in session:
        try:
            conn=get_db(); cur=conn.cursor(dictionary=True)
            cur.execute("SELECT COUNT(*) AS c FROM notifications WHERE user_id=%s AND is_read=0",(session['user_id'],))
            nc=cur.fetchone()['c']; cur.close(); conn.close()
        except: pass
    return {'notif_count':nc,'current_year':datetime.now().year}

if __name__=='__main__':
    app.run(debug=True,host='0.0.0.0',port=5000)
