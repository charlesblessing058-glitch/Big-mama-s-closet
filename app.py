import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from datetime import datetime

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
        return psycopg2.connect(DATABASE_URL, cursor_factory=DictCursor)
    else:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    conn = get_db()
    placeholder = '%s' if USE_POSTGRES else '?'
    
    conn.execute(f'''CREATE TABLE IF NOT EXISTS categories 
                 (id {'SERIAL' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'}, name TEXT UNIQUE)''')
    conn.execute(f'''CREATE TABLE IF NOT EXISTS products 
                 (id {'SERIAL' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'}, name TEXT, price REAL, original_price REAL, 
                  category TEXT, image_url TEXT, description TEXT, stock INTEGER, sold INTEGER DEFAULT 0)''')
    conn.execute(f'''CREATE TABLE IF NOT EXISTS admins 
                 (id {'SERIAL' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'}, username TEXT, password TEXT)''')
    conn.execute(f'''CREATE TABLE IF NOT EXISTS settings 
                 (id INTEGER PRIMARY KEY, logo_filename TEXT, about_text TEXT, notification_text TEXT, 
                  contact_phone TEXT, contact_email TEXT, contact_address TEXT)''')
    conn.execute(f'''CREATE TABLE IF NOT EXISTS blog_posts 
                 (id {'SERIAL' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'}, title TEXT, content TEXT, image_url TEXT, 
                  author TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, views INTEGER DEFAULT 0)''')
    conn.execute(f'''CREATE TABLE IF NOT EXISTS videos 
                 (id {'SERIAL' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'}, title TEXT, description TEXT, video_url TEXT, 
                  thumbnail_url TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.execute(f'''CREATE TABLE IF NOT EXISTS portfolio 
                 (id {'SERIAL' if USE_POSTGRES else 'INTEGER PRIMARY KEY AUTOINCREMENT'}, title TEXT, description TEXT, image_url TEXT, 
                  category TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    if conn.execute('SELECT COUNT(*) FROM admins').fetchone()[0] == 0:
        conn.execute(f'INSERT INTO admins (username, password) VALUES ({placeholder}, {placeholder})', ('admin', 'bigmama123'))
    
    if conn.execute('SELECT COUNT(*) FROM settings').fetchone()[0] == 0:
        conn.execute(f'INSERT INTO settings (logo_filename, about_text, notification_text, contact_phone, contact_email, contact_address) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})', 
                     ('logo.png', 'Welcome to Big Mama\'s Closet. We provide the finest fashion, beauty, and accessories in Kenya.', 
                      'Free delivery on orders over KES 5,000!', '+254 700 000 000', 'info@bigmamascloset.co.ke', 'Nairobi, Kenya'))
    
    if conn.execute('SELECT COUNT(*) FROM categories').fetchone()[0] == 0:
        for cat in ['Ladies Clothes', 'Men Clothes', 'Handbags', 'Shoes', 'Jewelry', 'Beauty']:
            try:
                conn.execute(f'INSERT INTO categories (name) VALUES ({placeholder})', (cat,))
            except:
                pass
    
    conn.commit()
    conn.close()

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def get_settings():
    conn = get_db()
    settings = conn.execute('SELECT * FROM settings WHERE id = 1').fetchone()
    conn.close()
    return settings

@app.route('/')
def home():
    conn = get_db()
    products = conn.execute('SELECT * FROM products').fetchall()
    categories = [row['name'] for row in conn.execute('SELECT * FROM categories ORDER BY name').fetchall()]
    conn.close()
    settings = get_settings()
    return render_template('index.html', products=products, categories=categories, settings=settings)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    conn = get_db()
    placeholder = '%s' if USE_POSTGRES else '?'
    products = conn.execute(f'SELECT * FROM products WHERE name LIKE {placeholder} OR description LIKE {placeholder}', 
                           (f'%{query}%', f'%{query}%')).fetchall()
    categories = [row['name'] for row in conn.execute('SELECT * FROM categories ORDER BY name').fetchall()]
    conn.close()
    settings = get_settings()
    return render_template('index.html', products=products, categories=categories, settings=settings, search_query=query)

@app.route('/about')
def about():
    settings = get_settings()
    return render_template('about.html', settings=settings)

@app.route('/contact')
def contact():
    settings = get_settings()
    return render_template('contact.html', settings=settings)

@app.route('/blog')
def blog():
    conn = get_db()
    posts = conn.execute('SELECT * FROM blog_posts ORDER BY created_at DESC').fetchall()
    conn.close()
    settings = get_settings()
    return render_template('blog.html', posts=posts, settings=settings)

@app.route('/blog/<int:post_id>')
def blog_post(post_id):
    conn = get_db()
    placeholder = '%s' if USE_POSTGRES else '?'
    conn.execute(f'UPDATE blog_posts SET views = views + 1 WHERE id = {placeholder}', (post_id,))
    conn.commit()
    post = conn.execute(f'SELECT * FROM blog_posts WHERE id = {placeholder}', (post_id,)).fetchone()
    conn.close()
    settings = get_settings()
    return render_template('blog_post.html', post=post, settings=settings)

@app.route('/videos')
def videos():
    conn = get_db()
    video_list = conn.execute('SELECT * FROM videos ORDER BY created_at DESC').fetchall()
    conn.close()
    settings = get_settings()
    return render_template('videos.html', videos=video_list, settings=settings)

@app.route('/portfolio')
def portfolio():
    conn = get_db()
    items = conn.execute('SELECT * FROM portfolio ORDER BY created_at DESC').fetchall()
    conn.close()
    settings = get_settings()
    return render_template('portfolio.html', items=items, settings=settings)

@app.route('/category/<category_name>')
def category(category_name):
    conn = get_db()
    placeholder = '%s' if USE_POSTGRES else '?'
    products = conn.execute(f'SELECT * FROM products WHERE category = {placeholder}', (category_name,)).fetchall()
    categories = [row['name'] for row in conn.execute('SELECT * FROM categories ORDER BY name').fetchall()]
    conn.close()
    settings = get_settings()
    return render_template('index.html', products=products, categories=categories, current_category=category_name, settings=settings)

@app.route('/product/<int:product_id>')
def product(product_id):
    conn = get_db()
    placeholder = '%s' if USE_POSTGRES else '?'
    product = conn.execute(f'SELECT * FROM products WHERE id = {placeholder}', (product_id,)).fetchone()
    conn.close()
    settings = get_settings()
    return render_template('product.html', product=product, settings=settings)

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    conn = get_db()
    placeholder = '%s' if USE_POSTGRES else '?'
    product = conn.execute(f'SELECT * FROM products WHERE id = {placeholder}', (product_id,)).fetchone()
    conn.close()
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
    settings = get_settings()
    return render_template('cart.html', cart=cart, total=total, settings=settings)

@app.route('/checkout')
def checkout():
    settings = get_settings()
    return render_template('checkout.html', settings=settings)

@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    cart = session.get('cart', {})
    if str(product_id) in cart: del cart[str(product_id)]
    session['cart'] = cart
    return redirect(url_for('cart'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        placeholder = '%s' if USE_POSTGRES else '?'
        admin = conn.execute(f'SELECT * FROM admins WHERE username = {placeholder} AND password = {placeholder}', (username, password)).fetchone()
        conn.close()
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
    conn = get_db()
    total_products = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    total_sold = conn.execute('SELECT COALESCE(SUM(sold), 0) FROM products').fetchone()[0]
    total_revenue = conn.execute('SELECT COALESCE(SUM(sold * price), 0) FROM products').fetchone()[0]
    total_posts = conn.execute('SELECT COUNT(*) FROM blog_posts').fetchone()[0]
    total_videos = conn.execute('SELECT COUNT(*) FROM videos').fetchone()[0]
    conn.close()
    return render_template('admin/dashboard.html', total_products=total_products, total_sold=total_sold, 
                         total_revenue=total_revenue, total_posts=total_posts, total_videos=total_videos)

@app.route('/admin/products')
@login_required
def admin_products():
    conn = get_db()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return render_template('admin/products.html', products=products)

@app.route('/admin/categories')
@login_required
def admin_categories():
    conn = get_db()
    categories = conn.execute('SELECT * FROM categories ORDER BY name').fetchall()
    conn.close()
    return render_template('admin/categories.html', categories=categories)

@app.route('/admin/categories/add', methods=['POST'])
@login_required
def add_category():
    name = request.form['name']
    conn = get_db()
    placeholder = '%s' if USE_POSTGRES else '?'
    try:
        conn.execute(f'INSERT INTO categories (name) VALUES ({placeholder})', (name,))
        conn.commit()
        flash('Category added!', 'success')
    except:
        flash('Category already exists!', 'danger')
    conn.close()
    return redirect(url_for('admin_categories'))

@app.route('/admin/categories/delete/<int:id>')
@login_required
def delete_category(id):
    conn = get_db()
    placeholder = '%s' if USE_POSTGRES else '?'
    conn.execute(f'DELETE FROM categories WHERE id = {placeholder}', (id,))
    conn.commit()
    conn.close()
    flash('Category deleted.', 'warning')
    return redirect(url_for('admin_categories'))

@app.route('/admin/blog')
@login_required
def admin_blog():
    conn = get_db()
    posts = conn.execute('SELECT * FROM blog_posts ORDER BY created_at DESC').fetchall()
    conn.close()
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
        
        conn = get_db()
        placeholder = '%s' if USE_POSTGRES else '?'
        conn.execute(f'INSERT INTO blog_posts (title, content, author, image_url) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})',
                    (title, content, author, image_url))
        conn.commit()
        conn.close()
        flash('Blog post created!', 'success')
        return redirect(url_for('admin_blog'))
    return render_template('admin/blog_form.html', post=None)

@app.route('/admin/blog/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_blog_post(id):
    conn = get_db()
    placeholder = '%s' if USE_POSTGRES else '?'
    post = conn.execute(f'SELECT * FROM blog_posts WHERE id = {placeholder}', (id,)).fetchone()
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
        
        conn.execute(f'UPDATE blog_posts SET title={placeholder}, content={placeholder}, author={placeholder}, image_url={placeholder} WHERE id={placeholder}',
                    (title, content, author, image_url, id))
        conn.commit()
        conn.close()
        flash('Blog post updated!', 'success')
        return redirect(url_for('admin_blog'))
    conn.close()
    return render_template('admin/blog_form.html', post=post)

@app.route('/admin/blog/delete/<int:id>')
@login_required
def delete_blog_post(id):
    conn = get_db()
    placeholder = '%s' if USE_POSTGRES else '?'
    conn.execute(f'DELETE FROM blog_posts WHERE id = {placeholder}', (id,))
    conn.commit()
    conn.close()
    flash('Blog post deleted.', 'warning')
    return redirect(url_for('admin_blog'))

@app.route('/admin/videos')
@login_required
def admin_videos():
    conn = get_db()
    video_list = conn.execute('SELECT * FROM videos ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('admin/videos.html', videos=video_list)

@app.route('/admin/videos/add', methods=['GET', 'POST'])
@login_required
def add_video():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        video_url = request.form['video_url']
        thumbnail_url = request.form.get('thumbnail_url', '')
        
        conn = get_db()
        placeholder = '%s' if USE_POSTGRES else '?'
        conn.execute(f'INSERT INTO videos (title, description, video_url, thumbnail_url) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})',
                    (title, description, video_url, thumbnail_url))
        conn.commit()
        conn.close()
        flash('Video added!', 'success')
        return redirect(url_for('admin_videos'))
    return render_template('admin/video_form.html', video=None)

@app.route('/admin/videos/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_video(id):
    conn = get_db()
    placeholder = '%s' if USE_POSTGRES else '?'
    video = conn.execute(f'SELECT * FROM videos WHERE id = {placeholder}', (id,)).fetchone()
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        video_url = request.form['video_url']
        thumbnail_url = request.form.get('thumbnail_url', '')
        
        conn.execute(f'UPDATE videos SET title={placeholder}, description={placeholder}, video_url={placeholder}, thumbnail_url={placeholder} WHERE id={placeholder}',
                    (title, description, video_url, thumbnail_url, id))
        conn.commit()
        conn.close()
        flash('Video updated!', 'success')
        return redirect(url_for('admin_videos'))
    conn.close()
    return render_template('admin/video_form.html', video=video)

@app.route('/admin/videos/delete/<int:id>')
@login_required
def delete_video(id):
    conn = get_db()
    placeholder = '%s' if USE_POSTGRES else '?'
    conn.execute(f'DELETE FROM videos WHERE id = {placeholder}', (id,))
    conn.commit()
    conn.close()
    flash('Video deleted.', 'warning')
    return redirect(url_for('admin_videos'))

@app.route('/admin/portfolio')
@login_required
def admin_portfolio():
    conn = get_db()
    items = conn.execute('SELECT * FROM portfolio ORDER BY created_at DESC').fetchall()
    conn.close()
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
        
        conn = get_db()
        placeholder = '%s' if USE_POSTGRES else '?'
        conn.execute(f'INSERT INTO portfolio (title, description, category, image_url) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})',
                    (title, description, category, image_url))
        conn.commit()
        conn.close()
        flash('Portfolio item added!', 'success')
        return redirect(url_for('admin_portfolio'))
    return render_template('admin/portfolio_form.html', item=None)

@app.route('/admin/portfolio/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_portfolio_item(id):
    conn = get_db()
    placeholder = '%s' if USE_POSTGRES else '?'
    item = conn.execute(f'SELECT * FROM portfolio WHERE id = {placeholder}', (id,)).fetchone()
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
        
        conn.execute(f'UPDATE portfolio SET title={placeholder}, description={placeholder}, category={placeholder}, image_url={placeholder} WHERE id={placeholder}',
                    (title, description, category, image_url, id))
        conn.commit()
        conn.close()
        flash('Portfolio item updated!', 'success')
        return redirect(url_for('admin_portfolio'))
    conn.close()
    return render_template('admin/portfolio_form.html', item=item)

@app.route('/admin/portfolio/delete/<int:id>')
@login_required
def delete_portfolio_item(id):
    conn = get_db()
    placeholder = '%s' if USE_POSTGRES else '?'
    conn.execute(f'DELETE FROM portfolio WHERE id = {placeholder}', (id,))
    conn.commit()
    conn.close()
    flash('Portfolio item deleted.', 'warning')
    return redirect(url_for('admin_portfolio'))

@app.route('/admin/products/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        original_price = request.form.get('original_price') or price
        category = request.form['category']
        description = request.form['description']
        stock = request.form['stock']
        image_url = request.form['image_url']
        
        if 'image_file' in request.files and request.files['image_file'].filename != '':
            file = request.files['image_file']
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = url_for('static', filename=f'uploads/{filename}')

        conn = get_db()
        placeholder = '%s' if USE_POSTGRES else '?'
        conn.execute(f'INSERT INTO products (name, price, original_price, category, description, stock, image_url, sold) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, 0)',
                     (name, price, original_price, category, description, stock, image_url))
        conn.commit()
        conn.close()
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin_products'))
    
    conn = get_db()
    categories = [row['name'] for row in conn.execute('SELECT * FROM categories ORDER BY name').fetchall()]
    conn.close()
    return render_template('admin/product_form.html', product=None, categories=categories)

@app.route('/admin/products/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    conn = get_db()
    placeholder = '%s' if USE_POSTGRES else '?'
    product = conn.execute(f'SELECT * FROM products WHERE id = {placeholder}', (id,)).fetchone()
    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        original_price = request.form.get('original_price') or price
        category = request.form['category']
        description = request.form['description']
        stock = request.form['stock']
        sold = request.form.get('sold', 0)
        image_url = product['image_url']
        
        if 'image_file' in request.files and request.files['image_file'].filename != '':
            file = request.files['image_file']
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = url_for('static', filename=f'uploads/{filename}')

        conn.execute(f'UPDATE products SET name={placeholder}, price={placeholder}, original_price={placeholder}, category={placeholder}, description={placeholder}, stock={placeholder}, sold={placeholder}, image_url={placeholder} WHERE id={placeholder}',
                     (name, price, original_price, category, description, stock, sold, image_url, id))
        conn.commit()
        conn.close()
        flash('Product updated!', 'success')
        return redirect(url_for('admin_products'))
    
    categories = [row['name'] for row in conn.execute('SELECT * FROM categories ORDER BY name').fetchall()]
    conn.close()
    return render_template('admin/product_form.html', product=product, categories=categories)

@app.route('/admin/products/delete/<int:id>')
@login_required
def delete_product(id):
    conn = get_db()
    placeholder = '%s' if USE_POSTGRES else '?'
    conn.execute(f'DELETE FROM products WHERE id = {placeholder}', (id,))
    conn.commit()
    conn.close()
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

        conn = get_db()
        placeholder = '%s' if USE_POSTGRES else '?'
        conn.execute(f'UPDATE settings SET about_text={placeholder}, notification_text={placeholder}, contact_phone={placeholder}, contact_email={placeholder}, contact_address={placeholder}, logo_filename={placeholder} WHERE id=1', 
                     (about_text, notification_text, contact_phone, contact_email, contact_address, logo_filename))
        conn.commit()
        conn.close()
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('admin_settings'))
    
    settings = get_settings()
    return render_template('admin/settings.html', settings=settings)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
