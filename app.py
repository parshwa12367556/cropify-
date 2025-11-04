from flask import Flask, request, jsonify, render_template
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_super_secret_key' # You can change this to any random string

# --- Database Setup ---
def get_db_connection():
    """Creates a connection to the SQLite database."""
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row # This allows accessing columns by name
    return conn

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE, password TEXT NOT NULL, role TEXT NOT NULL
        )
    ''')
    # Create products table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, category TEXT NOT NULL,
            price REAL NOT NULL, quantity INTEGER NOT NULL, image TEXT
        )
    ''')
    # Create feedback table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT, rating INTEGER NOT NULL, message TEXT NOT NULL
        )
    ''')
    # Create orders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_mode TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Initialize the database when the app starts
init_db()


# --- API Endpoints (for JavaScript to call) ---

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    name, email, password, role = data.get('name'), data.get('email'), data.get('password'), data.get('role')
    if not all([name, email, password, role]):
        return jsonify({'message': 'Missing required fields'}), 400
    try:
        conn = get_db_connection()
        # In a real app, you MUST hash the password here before saving
        conn.execute('INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)', (name, email, password, role))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Registration successful! Please log in.'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'message': 'This email is already registered.'}), 409
    except Exception as e:
        return jsonify({'message': f'An internal error occurred: {e}'}), 500

@app.route('/api/feedback', methods=['POST'])
def api_feedback():
    data = request.get_json()
    rating, message = data.get('rating'), data.get('message')
    if not all([rating, message]):
        return jsonify({'message': 'Rating and message are required.'}), 400
    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO feedback (rating, message) VALUES (?, ?)', (rating, message))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Thank you for your feedback!'}), 201
    except Exception as e:
        return jsonify({'message': f'An internal error occurred: {e}'}), 500

@app.route('/api/products', methods=['POST'])
def api_add_product():
    data = request.get_json()
    name, category, price, quantity, image = data.get('name'), data.get('category'), data.get('price'), data.get('quantity'), data.get('image')
    if not all([name, category, price, quantity]):
        return jsonify({'message': 'Missing required product fields'}), 400
    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO products (name, category, price, quantity, image) VALUES (?, ?, ?, ?, ?)', (name, category, float(price), int(quantity), image))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Product added successfully!'}), 201
    except Exception as e:
        return jsonify({'message': f'An internal error occurred: {e}'}), 500

@app.route('/api/products', methods=['GET'])
def api_get_products():
    """API endpoint to get all products."""
    try:
        conn = get_db_connection()
        products = conn.execute('SELECT * FROM products').fetchall()
        conn.close()
        return jsonify([dict(row) for row in products]), 200
    except Exception as e:
        return jsonify({'message': f'An internal error occurred: {e}'}), 500

@app.route('/api/admin/dashboard-data', methods=['GET'])
def api_admin_data():
    try:
        conn = get_db_connection()
        users = [dict(row) for row in conn.execute('SELECT id, name, email, role FROM users').fetchall()]
        products = [dict(row) for row in conn.execute('SELECT * FROM products').fetchall()]
        feedback = [dict(row) for row in conn.execute('SELECT rating, message FROM feedback').fetchall()]
        conn.close()
        return jsonify({'users': users, 'products': products, 'feedback': feedback}), 200
    except Exception as e:
        return jsonify({'message': f'An internal error occurred: {e}'}), 500


# --- HTML Page Routes (for browser navigation) ---
@app.route('/')
def index(): return render_template('index.html')
@app.route('/login')
def login(): return render_template('login.html')
@app.route('/register')
def register(): return render_template('register.html')
@app.route('/product')
def product(): return render_template('product.html')
@app.route('/feedback')
def feedback_page(): return render_template('feedback.html')
@app.route('/admin')
def admin(): return render_template('admin.html')
@app.route('/addproduct')
def addproduct(): return render_template('addproduct.html')
@app.route('/cart')
def cart(): return render_template('cart.html')

@app.route('/checkout', methods=['GET'])
def checkout():
    # In a real app, you'd pass cart totals etc. to the checkout page
    return render_template('checkout.html')

@app.route('/order-confirmation', methods=['POST'])
def order_confirmation():
    payment_mode = request.form.get('payment_mode')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO orders (payment_mode) VALUES (?)', (payment_mode,))
    order_id = cursor.lastrowid
    conn.commit()
    order = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    conn.close()
    return render_template('orderconformation.html', order=order)

@app.route('/thankyou')
def thankyou(): return render_template('thankyou.html')
@app.route('/shipping_info')
def shipping_info(): return render_template('shipping_info.html')
@app.route('/return_policy')
def return_policy(): return render_template('return_policy.html')
@app.route('/faqs')
def faqs(): return render_template('faqs.html')
@app.route('/privacy_policy')
def privacy_policy(): return render_template('privacy_policy.html')
@app.route('/terms_and_conditions')
def terms_and_conditions(): return render_template('terms_and_conditions.html')



if __name__ == '__main__':
    app.run(debug=True)