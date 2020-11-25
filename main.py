from datetime import datetime
import mysql.connector
import timeago
import hashlib
from slugify import slugify
from flask import Flask, url_for, render_template, redirect, request, session

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="python"
)

cursor = db.cursor(dictionary=True)

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'


def md5(string):
    return hashlib.md5(string.encode()).hexdigest()


def categories():
    sql = "SELECT * FROM categories ORDER BY category_name ASC"
    cursor.execute(sql)
    cats = cursor.fetchall()
    return cats


def hasPost(url):
    sql = "SELECT post_id FROM posts WHERE post_url = %s"
    cursor.execute(sql, (url,))
    post = cursor.fetchone()
    return post


def hasUser(email):
    sql = "SELECT user_id FROM users WHERE user_email = %s"
    cursor.execute(sql, (email,))
    post = cursor.fetchone()
    return post


def timeAgo(date):
    return timeago.format(date, datetime.now(), 'tr')


app.jinja_env.globals.update(categories=categories)
app.jinja_env.filters['timeAgo'] = timeAgo


@app.route('/')
def home():
    sql = "SELECT * FROM posts " \
          "INNER JOIN users ON users.user_id = posts.post_user_id " \
          "INNER JOIN categories ON categories.category_id = posts.post_category_id " \
          "ORDER BY post_id DESC"
    cursor.execute(sql)
    posts = cursor.fetchall()
    return render_template('index.html', posts=posts)


@app.route('/category/<url>')
def category(url):
    cursor.execute("SELECT * FROM categories WHERE category_url = %s", (url,))
    cat = cursor.fetchone()

    if cat:
        sql = "SELECT * FROM posts " \
              "INNER JOIN users ON users.user_id = posts.post_user_id " \
              "INNER JOIN categories ON categories.category_id = posts.post_category_id " \
              "WHERE post_category_id = %s " \
              "ORDER BY post_id DESC"
        cursor.execute(sql, (cat['category_id'],))
        posts = cursor.fetchall()
        return render_template('category.html', category=cat, posts=posts)
    else:
        return redirect(url_for('home'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))

    error = ''
    if request.method == 'POST':
        if request.form['email'] == '':
            error = 'E-posta adresinizi belirtin.'
        elif request.form['password'] == '':
            error = 'Şifrenizi belirtin.'
        else:
            sql = "SELECT * FROM users WHERE user_email = %s && user_password = %s"
            cursor.execute(sql, (request.form['email'], md5(request.form['password']),))
            user = cursor.fetchone()
            if user:
                session['user_id'] = user['user_id']
                return redirect(url_for('home'))
            else:
                error = 'Girdiğiniz bilgilere ait kullanıcı bulunamadı.'

    return render_template('login.html', error=error)


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = ''
    if request.method == 'POST':
        if request.form['username'] == '':
            error = 'Adınızı ve soyadınız belirtin'
        elif request.form['email'] == '':
            error = 'E-posta adresinizi belirtin'
        elif request.form['password'] == '' or request.form['re_password'] == '':
            error = 'Şifrenizi belirtin.'
        elif request.form['password'] != request.form['re_password']:
            error = 'Girdiğiniz şifreler birbiriyle uyuşmuyor'
        elif hasUser(request.form['email']):
            error = 'Bu e-posta ile birisi zaten kayıtlı, başka bir tane deneyin'
        else:
            sql = "INSERT INTO users SET user_name = %s, user_email = %s, user_password = %s"
            cursor.execute(sql, (request.form['username'], request.form['email'], md5(request.form['password'])))
            db.commit()
            if cursor.rowcount:
                session['user_id'] = cursor.lastrowid
                return redirect(url_for('home'))
            else:
                error = 'Teknik bir problemden dolayı kaydınız oluşturulamadı'

    return render_template('register.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/post/<url>')
def post(url):
    sql = "SELECT * FROM posts " \
          "INNER JOIN users ON users.user_id = posts.post_user_id " \
          "INNER JOIN categories ON categories.category_id = posts.post_category_id " \
          "WHERE post_url = %s"
    cursor.execute(sql, (url,))
    post = cursor.fetchone()
    if post:
        return render_template('post.html', post=post)
    else:
        return redirect(url_for('home'))


@app.route('/new-post', methods=['GET', 'POST'])
def newPost():
    error = ''
    if request.method == 'POST':
        if request.form['title'] == '':
            error = 'Makale başlığını belirtin'
        elif request.form['category_id'] == '':
            error = 'Makale kategorisini seçin'
        elif request.form['content'] == '':
            error = 'Makale içeriğini yazın'
        elif hasPost(slugify(request.form['title'])):
            error = 'Makale zaten ekli, başka bir ad deneyin'
        else:
            sql = "INSERT INTO posts SET post_title = %s, post_url = %s, post_content = %s, post_user_id = %s, post_category_id = %s"
            cursor.execute(sql, (
                request.form['title'], slugify(request.form['title']), request.form['content'], session['user_id'],
                request.form['category_id'],))
            db.commit()
            if cursor.rowcount:
                return redirect(url_for('post', url=slugify(request.form['title'])))
            else:
                error = 'Teknik bir problemden dolayı makaleniz eklenemedi'

    return render_template('new-post.html', error=error)


@app.errorhandler(404)
def page_not_found(error):
    return render_template('not-found.html'), 404
