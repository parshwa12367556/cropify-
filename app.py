# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(200))
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    payment_mode = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Create tables
with app.app_context():
    db.create_all()
    # Create admin user if not exists
    if not User.query.filter_by(role='admin').first():
        admin_user = User(
            name='Admin',
            email='admin@agrimarket.com',
            password=generate_password_hash('admin123'),
            role='admin'
        )
        db.session.add(admin_user)
        db.session.commit()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['user_role'] = user.role
            
            flash('Login successful!', 'success')
            
            if user.role == 'admin':
                return redirect(url_for('admin'))
            elif user.role == 'seller':
                return redirect(url_for('product'))
            else:
                return redirect(url_for('product'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
        
        new_user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            role=role
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/product')
def product():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    category = request.args.get('category', 'all')
    
    if category == 'all':
        product = Product.query.all()
    else:
        product = Product.query.filter_by(category=category).all()
    return render_template('product.html', product=product, category=category)

@app.route('/addproduct', methods=['GET', 'POST'])
def addproduct():
    if 'user_id' not in session or session['user_role'] != 'seller':
        flash('Access denied. Seller only.', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        price = float(request.form['price'])
        quantity = int(request.form['quantity'])
        image = request.form['image'] or None
        
        new_product = Product(
            name=name,
            category=category,
            price=price,
            quantity=quantity,
            image=image,
            seller_id=session['user_id']
        )
        
        db.session.add(new_product)
        db.session.commit()
        
        flash(f'Product "{name}" added successfully with ID: {new_product.id}', 'success')
        return redirect(url_for('product'))
    
    return render_template('addproduct.html')

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    if 'user_id' not in session or session['user_role'] != 'buyer':
        flash('Please login as a buyer first', 'error')
        return redirect(url_for('login'))
    
    product = Product.query.get_or_404(product_id)
    
    cart_item = Cart.query.filter_by(
        buyer_id=session['user_id'], 
        product_id=product_id
    ).first()
    
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = Cart(
            buyer_id=session['user_id'],
            product_id=product_id,
            quantity=1
        )
        db.session.add(cart_item)
    
    db.session.commit()
    flash('Product added to cart!', 'success')
    return redirect(url_for('product'))

@app.route('/cart')
def cart():
    if 'user_id' not in session or session['user_role'] != 'buyer':
        flash('Please login as a buyer first', 'error')
        return redirect(url_for('login'))
    
    cart_items = Cart.query.filter_by(buyer_id=session['user_id']).all()
    cart_product = []
    total_amount = 0
    
    for item in cart_items:
        product = Product.query.get(item.product_id)
        item_total = product.price * item.quantity
        total_amount += item_total
        cart_product.append({
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'quantity': item.quantity,
            'total': item_total,
            'image': product.image
        })
    
    return render_template('cart.html', cart_product=cart_product, total_amount=total_amount)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session or session['user_role'] != 'buyer':
        flash('Please login as a buyer first', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        payment_mode = request.form['payment_mode']
        
        cart_items = Cart.query.filter_by(buyer_id=session['user_id']).all()
        total_amount = 0
        
        for item in cart_items:
            product = Product.query.get(item.product_id)
            total_amount += product.price * item.quantity
        
        new_order = Order(
            buyer_id=session['user_id'],
            total_amount=total_amount,
            payment_mode=payment_mode,
            status='Confirmed'
        )
        
        db.session.add(new_order)
        Cart.query.filter_by(buyer_id=session['user_id']).delete()
        db.session.commit()
        
        flash('Order placed successfully!', 'success')
        return redirect(url_for('orderconformation', order_id=new_order.id))
    
    cart_items = Cart.query.filter_by(buyer_id=session['user_id']).all()
    total_amount = 0
    
    for item in cart_items:
        product = Product.query.get(item.product_id)
        total_amount += product.price * item.quantity
    
    return render_template('checkout.html', total_amount=total_amount)

@app.route('/orderconformation/<int:order_id>')
def orderconformation(order_id):
    if 'user_id' not in session:
        flash('Please login to view your order', 'error')
        return redirect(url_for('login'))
    
    order = Order.query.get_or_404(order_id)
    return render_template('orderconformation.html', order=order)


@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if 'user_id' not in session:
        flash('Please login first', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        rating = request.form['rating']
        message = request.form['message']
        
        new_feedback = Feedback(
            buyer_id=session['user_id'],
            rating=rating,
            message=message
        )
        
        db.session.add(new_feedback)
        db.session.commit()
        
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('thankyou'))
    
    return render_template('feedback.html')

@app.route('/admin')
def admin():
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('Access denied. Admin only.', 'error')
        return redirect(url_for('index'))
    
    today = datetime.now().date()
    today_orders = Order.query.filter(
        db.func.date(Order.created_at) == today
    ).all()
    
    today_sales = sum(order.total_amount for order in today_orders)
    all_orders = Order.query.all()
    all_feedback = Feedback.query.all()
    all_products = Product.query.all()
    
    return render_template('admin.html', 
                         today_sales=today_sales,
                         orders=all_orders,
                         feedback=all_feedback,
                         products=all_products)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

# Static Pages
@app.route('/shipping_info')
def shipping_info():
    return render_template('shipping_info.html')

@app.route('/return_policy')
def return_policy():
    return render_template('return_policy.html')

@app.route('/faqs')
def faqs():
    return render_template('faqs.html')

@app.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/terms_and_conditions')
def terms_and_conditions():
    return render_template('terms_and_conditions.html')

if __name__ == '__main__':
    app.run(debug=True)
