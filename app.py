import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'big_mama_closet_secret_key_2026')

DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    import psycopg2
    from psycopg2.extras import DictCursor
    USE_POSTGRES = True
else:
    import sqlite3
    DATABASE = 'shop.db'
    USE_POSTGRES = False

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db():
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL)
    else:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return conn

def db_query(query, params=()):
    conn = get_db()
    if USE_POSTGRES:
        cur = conn.cursor(cursor_factory=DictCursor)
        cur.execute(query, params)
        result = cur.fetchall()
    else:
        result = conn.execute(query, params).fetchall()
    conn.close()
    return result

def db_fetch_one(query, params=()):
    conn = get_db()
    if USE_POSTGRES:
        cur = conn.cursor(cursor_factory=DictCursor)
        cur.execute(query, params)
        result = cur.fetchone()
    else:
        result = conn.execute(query, params).fetchone()
    conn.close()
    return result

def db_execute(query, params=()):
    conn = get_db()
    if USE_POSTGRES:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
    else:
        conn.execute(query, params)
        conn.commit()
    conn.close()

def init_db():
    if USE_POSTGRES:
        db_execute('''CREATE TABLE IF NOT EXISTS categories (id SERIAL PRIMARY KEY, name TEXT UNIQUE)''')
        db_execute('''CREATE TABLE IF NOT EXISTS products (id SERIAL PRIMARY KEY, name TEXT, price REAL, original_price REAL, category TEXT, image_url TEXT, description TEXT, stock INTEGER, sold INTEGER DEFAULT 0)''')
        db_execute('''CREATE TABLE IF NOT EXISTS admins (id SERIAL PRIMARY KEY, username TEXT, password TEXT)''')
        db_execute('''CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, logo_filename TEXT, about_text TEXT, notification_text TEXT, contact_phone TEXT, contact_email TEXT, contact_address TEXT)''')
        db_execute('''CREATE TABLE IF NOT EXISTS blog_posts (id SERIAL PRIMARY KEY, title TEXT, content TEXT, image_url TEXT, author TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, views INTEGER DEFAULT 0)''')
        db_execute('''CREATE TABLE IF NOT EXISTS videos (id SERIAL PRIMARY KEY, title TEXT, description TEXT, video_url TEXT, thumbnail_url TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        db_execute('''CREATE TABLE IF NOT EXISTS portfolio (id SERIAL PRIMARY KEY, title TEXT, description TEXT, image_url TEXT, category TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        if db_fetch_one('SELECT COUNT(*) FROM admins')[0] == 0:
            db_execute('INSERT INTO admins (username, password) VALUES (%s, %s)', ('admin', 'bigmama123'))
        if db_fetch_one('SELECT COUNT(*) FROM settings')[0] == 0:
            db_execute('INSERT INTO settings (id, logo_filename, about_text, notification_text, contact_phone, contact_email, contact_address) VALUES (1, %s, %s, %s, %s, %s, %s)', 
                       ('logo.png', 'Welcome to Big Mama\'s Closet.', 'Free delivery on orders over KES 5,000!', '+254 700 000 000', 'info@bigmamascloset.co.ke', 'Nairobi, Kenya'))
        if db_fetch_one('SELECT COUNT(*) FROM categories')[0] == 0:
            for cat in ['Ladies Clothes', 'Men Clothes', 'Handbags', 'Shoes', 'Jewelry', 'Beauty']:
                try: db_execute('INSERT INTO categories (name) VALUES (%s)', (cat,))
                except: pass
    else:
        db_execute('''CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)''')
        db_execute('''CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price REAL, original_price REAL, category TEXT, image_url TEXT, description TEXT, stock INTEGER, sold INTEGER DEFAULT 0)''')
        db_execute('''CREATE TABLE IF NOT EXISTS admins (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT)''')
        db_execute('''CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY, logo_filename TEXT, about_text TEXT, notification_text TEXT, contact_phone TEXT, contact_email TEXT, contact_address TEXT)''')
        db_execute('''CREATE TABLE IF NOT EXISTS blog_posts (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT, image_url TEXT, author TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, views INTEGER DEFAULT 0)''')
        db_execute('''CREATE TABLE IF NOT EXISTS videos (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, description TEXT, video_url TEXT, thumbnail_url TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        db_execute('''CREATE TABLE IF NOT EXISTS portfolio (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, description TEXT, image_url TEXT, category TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        if db_fetch_one('SELECT COUNT(*) FROM admins')[0] == 0:
            db_execute('INSERT INTO admins (username, password) VALUES (?, ?)', ('admin', 'bigmama123'))
        if db_fetch_one('SELECT COUNT(*) FROM settings')[0] == 0:
            db_execute('INSERT INTO settings (id, logo_filename, about_text, notification_text, contact_phone, contact_email, contact_address) VALUES (1, ?, ?, ?, ?, ?, ?)', 
                       ('logo.png', 'Welcome to Big Mama\'s Closet.', 'Free delivery on orders over KES 5,000!', '+254 700 000 000', 'info@bigmamascloset.co.ke', 'Nairobi, Kenya'))
        if db_fetch_one('SELECT COUNT(*) FROM categories')[0] == 0:
            for cat in ['Ladies Clothes', 'Men Clothes', 'Handbags', 'Shoes', 'Jewelry', 'Beauty']:
                db_execute('INSERT INTO categories (name) VALUES (?)', (cat,))

# Initialize the database when the app starts
init_db()

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def get_settings():
    return db_fetch_one('SELECT * FROM settings WHERE id = 1')

# --- PUBLIC ROUTES ---
@app.route('/')
def home():
    products = db_query('SELECT * FROM products')
    categories = [row['name'] for row in db_query('SELECT * FROM categories ORDER BY name')]
    return render_template('index.html', products=products, categories=categories, settings=get_settings())

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if USE_POSTGRES:
        products = db_query('SELECT * FROM products WHERE name ILIKE %s OR description ILIKE %s', (f'%{query}%', f'%{query}%'))
    else:
        products = db_query('SELECT * FROM products WHERE name LIKE ? OR description LIKE ?', (f'%{query}%', f'%{query}%'))
    categories = [row['name'] for row in db_query('SELECT * FROM categories ORDER BY name')]
    return render_template('index.html', products=products, categories=categories, settings=get_settings(), search_query=query)

@app.route('/about')
def about():
    return render_template('about.html', settings=get_settings())

@app.route('/contact')
def contact():
    return render_template('contact.html', settings=get_settings())

@app.route('/blog')
def blog():
    posts = db_query('SELECT * FROM blog_posts ORDER BY created_at DESC')
    return render_template('blog.html', posts=posts, settings=get_settings())

@app.route('/blog/<int:post_id>')
def blog_post(post_id):
    db_execute('UPDATE blog_posts SET views = views + 1 WHERE id = %s' if USE_POSTGRES else 'UPDATE blog_posts SET views = views + 1 WHERE id = ?', (post_id,))
    post = db_fetch_one('SELECT * FROM blog_posts WHERE id = %s' if USE_POSTGRES else 'SELECT * FROM blog_posts WHERE id = ?', (post_id,))
    return render_template('blog_post.html', post=post, settings=get_settings())

@app.route('/videos')
def videos():
    video_list = db_query('SELECT * FROM videos ORDER BY created_at DESC')
    return render_template('videos.html', videos=video_list, settings=get_settings())

@app.route('/portfolio')
def portfolio():
    items = db_query('SELECT * FROM portfolio ORDER BY created_at DESC')
    return render_template('portfolio.html', items=items, settings=get_settings())

@app.route('/category/<category_name>')
def category(category_name):
    products = db_query('SELECT * FROM products WHERE category = %s' if USE_POSTGRES else 'SELECT * FROM products WHERE category = ?', (category_name,))
    categories = [row['name'] for row in db_query('SELECT * FROM categories ORDER BY name')]
    return render_template('index.html', products=products, categories=categories, current_category=category_name, settings=get_settings())

@app.route('/product/<int:product_id>')
def product(product_id):
    product = db_fetch_one('SELECT * FROM products WHERE id = %s' if USE_POSTGRES else 'SELECT * FROM products WHERE id = ?', (product_id,))
    return render_template('product.html', product=product, settings=get_settings())

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    product = db_fetch_one('SELECT * FROM products WHERE id = %s' if USE_POSTGRES else 'SELECT * FROM products WHERE id = ?', (product_id,))
    cart = session.get('cart', {})
    str_id = str(product_id)
    cart[str_id] = cart.get(str_id, {'name': product['name'], 'price': product['price'], 'quantity': 0, 'image': product['image_url']})
    cart[str_id]['quantity'] += 1
    session['cart'] = cart
    flash(f'{product["name"]} added to bag!', 'success')
    return redirect(request.referrer or url_for('home'))

@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    total = sum(float(item['price']) * int(item['quantity']) for item in cart.values())
    return render_template('cart.html', cart=cart, total=total, settings=get_settings())

@app.route('/checkout')
def checkout():
    return render_template('checkout.html', settings=get_settings())

@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    cart = session.get('cart', {})
    if str(product_id) in cart: del cart[str(product_id)]
    session['cart'] = cart
    return redirect(url_for('cart'))

# --- ADMIN ROUTES ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin = db_fetch_one('SELECT * FROM admins WHERE username = %s AND password = %s' if USE_POSTGRES else 'SELECT * FROM admins WHERE username = ? AND password = ?', (username, password))
        if admin:
            session['admin_id'] = admin['id']
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
@login_required
def admin_dashboard():
    total_products = db_fetch_one('SELECT COUNT(*) FROM products')[0]
    total_sold = db_fetch_one('SELECT COALESCE(SUM(sold), 0) FROM products')[0]
    total_revenue = db_fetch_one('SELECT COALESCE(SUM(sold * price), 0) FROM products')[0]
    total_posts = db_fetch_one('SELECT COUNT(*) FROM blog_posts')[0]
    total_videos = db_fetch_one('SELECT COUNT(*) FROM videos')[0]
    return render_template('admin/dashboard.html', total_products=total_products, total_sold=total_sold, total_revenue=total_revenue, total_posts=total_posts, total_videos=total_videos)

@app.route('/admin/products')
@login_required
def admin_products():
    products = db_query('SELECT * FROM products')
    return render_template('admin/products.html', products=products)

@app.route('/admin/categories')
@login_required
def admin_categories():
    categories = db_query('SELECT * FROM categories ORDER BY name')
    return render_template('admin/categories.html', categories=categories)

@app.route('/admin/categories/add', methods=['POST'])
@login_required
def add_category():
    name = request.form['name']
    try:
        db_execute('INSERT INTO categories (name) VALUES (%s)' if USE_POSTGRES else 'INSERT INTO categories (name) VALUES (?)', (name,))
        flash('Category added!', 'success')
    except:
        flash('Category already exists!', 'danger')
    return redirect(url_for('admin_categories'))

@app.route('/admin/categories/delete/<int:id>')
@login_required
def delete_category(id):
    db_execute('DELETE FROM categories WHERE id = %s' if USE_POSTGRES else 'DELETE FROM categories WHERE id = ?', (id,))
    flash('Category deleted.', 'warning')
    return redirect(url_for('admin_categories'))

@app.route('/admin/blog')
@login_required
def admin_blog():
    posts = db_query('SELECT * FROM blog_posts ORDER BY created_at DESC')
    return render_template('admin/blog.html', posts=posts)

@app.route('/admin/blog/add', methods=['GET', 'POST'])
@login_required
def add_blog_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        author = request.form['author']
        image_url = request.form['image_url']
        if 'image_file' in request.files and request.files['image_file'].filename != '':
            file = request.files['image_file']
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = url_for('static', filename=f'uploads/{filename}')
        db_execute('INSERT INTO blog_posts (title, content, author, image_url) VALUES (%s, %s, %s, %s)' if USE_POSTGRES else 'INSERT INTO blog_posts (title, content, author, image_url) VALUES (?, ?, ?, ?)', (title, content, author, image_url))
        flash('Blog post created!', 'success')
        return redirect(url_for('admin_blog'))
    return render_template('admin/blog_form.html', post=None)

@app.route('/admin/blog/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_blog_post(id):
    post = db_fetch_one('SELECT * FROM blog_posts WHERE id = %s' if USE_POSTGRES else 'SELECT * FROM blog_posts WHERE id = ?', (id,))
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        author = request.form['author']
        image_url = post['image_url']
        if 'image_file' in request.files and request.files['image_file'].filename != '':
            file = request.files['image_file']
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = url_for('static', filename=f'uploads/{filename}')
        db_execute('UPDATE blog_posts SET title=%s, content=%s, author=%s, image_url=%s WHERE id=%s' if USE_POSTGRES else 'UPDATE blog_posts SET title=?, content=?, author=?, image_url=? WHERE id=?', (title, content, author, image_url, id))
        flash('Blog post updated!', 'success')
        return redirect(url_for('admin_blog'))
    return render_template('admin/blog_form.html', post=post)

@app.route('/admin/blog/delete/<int:id>')
@login_required
def delete_blog_post(id):
    db_execute('DELETE FROM blog_posts WHERE id = %s' if USE_POSTGRES else 'DELETE FROM blog_posts WHERE id = ?', (id,))
    flash('Blog post deleted.', 'warning')
    return redirect(url_for('admin_blog'))

@app.route('/admin/videos')
@login_required
def admin_videos():
    video_list = db_query('SELECT * FROM videos ORDER BY created_at DESC')
    return render_template('admin/videos.html', videos=video_list)

@app.route('/admin/videos/add', methods=['GET', 'POST'])
@login_required
def add_video():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        video_url = request.form['video_url']
        thumbnail_url = request.form.get('thumbnail_url', '')
        db_execute('INSERT INTO videos (title, description, video_url, thumbnail_url) VALUES (%s, %s, %s, %s)' if USE_POSTGRES else 'INSERT INTO videos (title, description, video_url, thumbnail_url) VALUES (?, ?, ?, ?)', (title, description, video_url, thumbnail_url))
        flash('Video added!', 'success')
        return redirect(url_for('admin_videos'))
    return render_template('admin/video_form.html', video=None)

@app.route('/admin/videos/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_video(id):
    video = db_fetch_one('SELECT * FROM videos WHERE id = %s' if USE_POSTGRES else 'SELECT * FROM videos WHERE id = ?', (id,))
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        video_url = request.form['video_url']
        thumbnail_url = request.form.get('thumbnail_url', '')
        db_execute('UPDATE videos SET title=%s, description=%s, video_url=%s, thumbnail_url=%s WHERE id=%s' if USE_POSTGRES else 'UPDATE videos SET title=?, description=?, video_url=?, thumbnail_url=? WHERE id=?', (title, description, video_url, thumbnail_url, id))
        flash('Video updated!', 'success')
        return redirect(url_for('admin_videos'))
    return render_template('admin/video_form.html', video=video)

@app.route('/admin/videos/delete/<int:id>')
@login_required
def delete_video(id):
    db_execute('DELETE FROM videos WHERE id = %s' if USE_POSTGRES else 'DELETE FROM videos WHERE id = ?', (id,))
    flash('Video deleted.', 'warning')
    return redirect(url_for('admin_videos'))

@app.route('/admin/portfolio')
@login_required
def admin_portfolio():
    items = db_query('SELECT * FROM portfolio ORDER BY created_at DESC')
    return render_template('admin/portfolio.html', items=items)

@app.route('/admin/portfolio/add', methods=['GET', 'POST'])
@login_required
def add_portfolio_item():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        category = request.form['category']
        image_url = request.form['image_url']
        if 'image_file' in request.files and request.files['image_file'].filename != '':
            file = request.files['image_file']
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = url_for('static', filename=f'uploads/{filename}')
        db_execute('INSERT INTO portfolio (title, description, category, image_url) VALUES (%s, %s, %s, %s)' if USE_POSTGRES else 'INSERT INTO portfolio (title, description, category, image_url) VALUES (?, ?, ?, ?)', (title, description, category, image_url))
        flash('Portfolio item added!', 'success')
        return redirect(url_for('admin_portfolio'))
    return render_template('admin/portfolio_form.html', item=None)

@app.route('/admin/portfolio/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_portfolio_item(id):
    item = db_fetch_one('SELECT * FROM portfolio WHERE id = %s' if USE_POSTGRES else 'SELECT * FROM portfolio WHERE id = ?', (id,))
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        category = request.form['category']
        image_url = item['image_url']
        if 'image_file' in request.files and request.files['image_file'].filename != '':
            file = request.files['image_file']
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = url_for('static', filename=f'uploads/{filename}')
        db_execute('UPDATE portfolio SET title=%s, description=%s, category=%s, image_url=%s WHERE id=%s' if USE_POSTGRES else 'UPDATE portfolio SET title=?, description=?, category=?, image_url=? WHERE id=?', (title, description, category, image_url, id))
        flash('Portfolio item updated!', 'success')
        return redirect(url_for('admin_portfolio'))
    return render_template('admin/portfolio_form.html', item=item)

@app.route('/admin/portfolio/delete/<int:id>')
@login_required
def delete_portfolio_item(id):
    db_execute('DELETE FROM portfolio WHERE id = %s' if USE_POSTGRES else 'DELETE FROM portfolio WHERE id = ?', (id,))
    flash('Portfolio item deleted.', 'warning')
    return redirect(url_for('admin_portfolio'))

@app.route('/admin/products/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        original_price = float(request.form.get('original_price') or price)
        category = request.form['category']
        description = request.form['description']
        stock = int(request.form['stock'])
        # THIS FIXES THE DISAPPEARING LINK
        image_url = request.form.get('image_url', '').strip()
        
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        if 'image_file' in request.files and request.files['image_file'].filename != '':
            file = request.files['image_file']
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = url_for('static', filename=f'uploads/{filename}')
        elif not image_url:
            image_url = 'https://via.placeholder.com/300?text=No+Image'

        db_execute('INSERT INTO products (name, price, original_price, category, description, stock, image_url, sold) VALUES (%s, %s, %s, %s, %s, %s, %s, 0)' if USE_POSTGRES else 'INSERT INTO products (name, price, original_price, category, description, stock, image_url, sold) VALUES (?, ?, ?, ?, ?, ?, ?, 0)', (name, price, original_price, category, description, stock, image_url))
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin_products'))
    
    categories = [row['name'] for row in db_query('SELECT * FROM categories ORDER BY name')]
    return render_template('admin/product_form.html', product=None, categories=categories)

@app.route('/admin/products/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    product = db_fetch_one('SELECT * FROM products WHERE id = %s' if USE_POSTGRES else 'SELECT * FROM products WHERE id = ?', (id,))
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        original_price = float(request.form.get('original_price') or price)
        category = request.form['category']
        description = request.form['description']
        stock = int(request.form['stock'])
        sold = int(request.form.get('sold', 0))
        # THIS FIXES THE DISAPPEARING LINK
        image_url = request.form.get('image_url', '').strip()
        
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        if 'image_file' in request.files and request.files['image_file'].filename != '':
            file = request.files['image_file']
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = url_for('static', filename=f'uploads/{filename}')
        elif not image_url:
            image_url = product['image_url']

        db_execute('UPDATE products SET name=%s, price=%s, original_price=%s, category=%s, description=%s, stock=%s, sold=%s, image_url=%s WHERE id=%s' if USE_POSTGRES else 'UPDATE products SET name=?, price=?, original_price=?, category=?, description=?, stock=?, sold=?, image_url=? WHERE id=?', (name, price, original_price, category, description, stock, sold, image_url, id))
        flash('Product updated!', 'success')
        return redirect(url_for('admin_products'))
    
    categories = [row['name'] for row in db_query('SELECT * FROM categories ORDER BY name')]
    return render_template('admin/product_form.html', product=product, categories=categories)

@app.route('/admin/products/delete/<int:id>')
@login_required
def delete_product(id):
    db_execute('DELETE FROM products WHERE id = %s' if USE_POSTGRES else 'DELETE FROM products WHERE id = ?', (id,))
    flash('Product deleted.', 'warning')
    return redirect(url_for('admin_products'))

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    if request.method == 'POST':
        about_text = request.form['about_text']
        notification_text = request.form['notification_text']
        contact_phone = request.form['contact_phone']
        contact_email = request.form['contact_email']
        contact_address = request.form['contact_address']
        logo_filename = get_settings()['logo_filename']
        if 'logo_file' in request.files and request.files['logo_file'].filename != '':
            file = request.files['logo_file']
            filename = secure_filename(file.filename)
            file.save(os.path.join('static', filename))
            logo_filename = filename
        db_execute('UPDATE settings SET about_text=%s, notification_text=%s, contact_phone=%s, contact_email=%s, contact_address=%s, logo_filename=%s WHERE id=1' if USE_POSTGRES else 'UPDATE settings SET about_text=?, notification_text=?, contact_phone=?, contact_email=?, contact_address=?, logo_filename=? WHERE id=1', (about_text, notification_text, contact_phone, contact_email, contact_address, logo_filename))
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('admin_settings'))
    return render_template('admin/settings.html', settings=get_settings())

if __name__ == '__main__':
    app.run(debug=True, port=5000)
