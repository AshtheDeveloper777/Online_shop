import sys
import types

# Robust pkg_resources polyfill for Python 3.12 / Vercel runtime
try:
    import pkg_resources
    if not hasattr(pkg_resources, 'DistributionNotFound'):
        class DummyDistributionNotFound(Exception):
            pass
        pkg_resources.DistributionNotFound = DummyDistributionNotFound
except ImportError:
    class DummyDistributionNotFound(Exception):
        pass

    class DummyDistribution:
        version = "1.4.2"

    pkg_resources = types.ModuleType("pkg_resources")
    pkg_resources.DistributionNotFound = DummyDistributionNotFound
    pkg_resources.get_distribution = lambda name: DummyDistribution()
    sys.modules["pkg_resources"] = pkg_resources

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import stripe
import razorpay
import requests
import hmac
import hashlib
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

IS_VERCEL = bool(os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'))

db_url = os.environ.get('DATABASE_URL')

if db_url:
    # Fix legacy postgres:// scheme to postgresql:// for SQLAlchemy
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['UPLOAD_FOLDER'] = '/tmp/static/uploads' if IS_VERCEL else 'static/uploads'
elif IS_VERCEL:
    db_path = '/tmp/ecommerce.db'
    src_db = os.path.join(os.path.dirname(__file__), 'instance', 'ecommerce.db')
    if not os.path.exists(src_db):
        src_db = os.path.join(os.path.dirname(__file__), 'ecommerce.db')
    
    if not os.path.exists(db_path) and os.path.exists(src_db):
        import shutil
        try:
            shutil.copyfile(src_db, db_path)
        except Exception as e:
            print(f"Error copying initial DB to /tmp: {e}")
            
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['UPLOAD_FOLDER'] = '/tmp/static/uploads'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecommerce.db'
    app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Inject cart_count into all rendered templates automatically
@app.context_processor
def inject_cart_count():
    cart_count = 0
    if current_user.is_authenticated:
        try:
            cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
            cart_count = sum(item.quantity for item in cart_items)
        except Exception:
            cart_count = 0
    return dict(cart_count=cart_count)

_db_initialized = False

@app.before_request
def ensure_db_initialized():
    global _db_initialized
    if not _db_initialized:
        try:
            db.create_all()
            if Product.query.count() == 0:
                sample_products = [
                    Product(name='MacBook Pro 16"', description='Powerful laptop with M3 chip, 16GB RAM, 512GB SSD. Perfect for professionals and creatives.', price=2499.99, stock=15, category='Electronics', image_url='https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=800&auto=format&fit=crop&q=80'),
                    Product(name='Wireless Gaming Mouse', description='Ergonomic wireless mouse with 12,000 DPI sensor, RGB lighting, and 50-hour battery life.', price=79.99, stock=50, category='Electronics', image_url='https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=800&auto=format&fit=crop&q=80'),
                    Product(name='Mechanical RGB Keyboard', description='Full RGB mechanical gaming keyboard with Cherry MX switches and aluminum frame.', price=149.99, stock=30, category='Electronics', image_url='https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=800&auto=format&fit=crop&q=80'),
                    Product(name='Premium Gaming Headset', description='7.1 Surround sound wireless gaming headset with noise cancellation and RGB lighting.', price=199.99, stock=25, category='Electronics', image_url='https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800&auto=format&fit=crop&q=80'),
                    Product(name='Apple Watch Series 9', description='Latest smartwatch with fitness tracking, ECG, blood oxygen monitoring, and always-on display.', price=399.99, stock=20, category='Electronics', image_url='https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=800&auto=format&fit=crop&q=80'),
                    Product(name='USB-C Multi-Port Hub', description='7-in-1 USB-C hub with HDMI, USB 3.0 ports, SD card reader, and power delivery.', price=89.99, stock=40, category='Accessories', image_url='https://images.unsplash.com/photo-1625842268584-8f3296236761?w=800&auto=format&fit=crop&q=80'),
                    Product(name='Ergonomic Laptop Stand', description='Adjustable aluminum laptop stand with ventilation slots and cable management.', price=59.99, stock=35, category='Accessories', image_url='https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=800&auto=format&fit=crop&q=80'),
                    Product(name='4K Webcam Pro', description='1080p HD webcam with auto-focus, noise cancellation, and privacy shutter.', price=129.99, stock=20, category='Electronics', image_url='https://images.unsplash.com/photo-1585060544812-6b45742d762f?w=800&auto=format&fit=crop&q=80'),
                    Product(name='Wireless Earbuds Pro', description='Premium wireless earbuds with active noise cancellation and 30-hour battery life.', price=179.99, stock=45, category='Electronics', image_url='https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=800&auto=format&fit=crop&q=80'),
                    Product(name='Portable SSD 1TB', description='Ultra-fast external SSD with USB-C connectivity, perfect for backups and file transfers.', price=129.99, stock=30, category='Accessories', image_url='https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?w=800&auto=format&fit=crop&q=80'),
                    Product(name='Monitor 27" 4K', description='27-inch 4K UHD monitor with HDR, 144Hz refresh rate, and USB-C connectivity.', price=449.99, stock=12, category='Electronics', image_url='https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=800&auto=format&fit=crop&q=80'),
                    Product(name='Mechanical Keyboard TKL', description='Tenkeyless mechanical keyboard with RGB backlighting and premium keycaps.', price=119.99, stock=28, category='Electronics', image_url='https://images.unsplash.com/photo-1618384887929-16ec33fab9ef?w=800&auto=format&fit=crop&q=80'),
                ]
                for product in sample_products:
                    db.session.add(product)
                db.session.commit()
            else:
                # Auto-repair legacy placeholder URLs in database
                old_products = Product.query.filter(Product.image_url.like('%via.placeholder.com%')).all()
                if old_products:
                    url_map = {
                        'MacBook Pro 16"': 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=800&auto=format&fit=crop&q=80',
                        'Wireless Gaming Mouse': 'https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=800&auto=format&fit=crop&q=80',
                        'Mechanical RGB Keyboard': 'https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=800&auto=format&fit=crop&q=80',
                        'Premium Gaming Headset': 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800&auto=format&fit=crop&q=80',
                        'Apple Watch Series 9': 'https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=800&auto=format&fit=crop&q=80',
                        'USB-C Multi-Port Hub': 'https://images.unsplash.com/photo-1625842268584-8f3296236761?w=800&auto=format&fit=crop&q=80',
                        'Ergonomic Laptop Stand': 'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=800&auto=format&fit=crop&q=80',
                        '4K Webcam Pro': 'https://images.unsplash.com/photo-1585060544812-6b45742d762f?w=800&auto=format&fit=crop&q=80',
                        'Wireless Earbuds Pro': 'https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=800&auto=format&fit=crop&q=80',
                        'Portable SSD 1TB': 'https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?w=800&auto=format&fit=crop&q=80',
                        'Monitor 27" 4K': 'https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=800&auto=format&fit=crop&q=80',
                        'Mechanical Keyboard TKL': 'https://images.unsplash.com/photo-1618384887929-16ec33fab9ef?w=800&auto=format&fit=crop&q=80',
                    }
                    for p in old_products:
                        p.image_url = url_map.get(p.name, 'https://images.unsplash.com/photo-1526738549149-8e07eca6c147?w=800&auto=format&fit=crop&q=80')
            _db_initialized = True
        except Exception as e:
            print(f"Error in ensure_db_initialized: {e}")
            try:
                db.session.rollback()
            except Exception:
                pass
            _db_initialized = True

@app.errorhandler(500)
def handle_500_error(e):
    import traceback
    try:
        db.session.rollback()
    except Exception:
        pass
    error_trace = traceback.format_exc()
    print(f"500 Internal Error: {e}\n{error_trace}")
    return f"<h1>500 Internal Server Error</h1><p><b>Error Details:</b> {e}</p><pre>{error_trace}</pre>", 500

# Payment Gateway Configuration

# Stripe configuration (use test keys)
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')

# Check if Stripe is configured
STRIPE_ENABLED = bool(STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY and 
                      STRIPE_SECRET_KEY.startswith('sk_') and 
                      STRIPE_PUBLISHABLE_KEY.startswith('pk_'))

if STRIPE_ENABLED:
    stripe.api_key = STRIPE_SECRET_KEY
else:
    stripe.api_key = None

# Razorpay configuration (for UPI, Cards, Wallets, Netbanking)
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', 'rzp_test_S8B6b25tETdizs')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '7K3XLSsfsZGqrBleXHe5bVHq')

# Check if Razorpay is configured
RAZORPAY_ENABLED = bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET and 
                        RAZORPAY_KEY_ID.startswith('rzp_'))

if RAZORPAY_ENABLED:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
else:
    razorpay_client = None

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship('Order', backref='user', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    stock = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    product = db.relationship('Product', backref='cart_items')

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    shipping_address = db.Column(db.Text, nullable=True)
    payment_status = db.Column(db.String(20), default='pending')
    payment_method = db.Column(db.String(20), default='mock')  # mock, stripe, razorpay
    stripe_payment_intent_id = db.Column(db.String(255), nullable=True)
    razorpay_order_id = db.Column(db.String(255), nullable=True)
    razorpay_payment_id = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    product = db.relationship('Product', backref='order_items')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/')
def index():
    products = Product.query.limit(8).all()
    return render_template('index.html', products=products)

@app.route('/products')
def products():
    category = request.args.get('category')
    search = request.args.get('search')
    query = Product.query
    
    if category:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(Product.name.contains(search) | Product.description.contains(search))
    
    products = query.all()
    categories = db.session.query(Product.category).distinct().all()
    categories = [cat[0] for cat in categories if cat[0]]
    
    return render_template('products.html', products=products, categories=categories, current_category=category)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_detail.html', product=product)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return redirect(url_for('register'))
        
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/cart')
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get('quantity', 1))
    
    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(user_id=current_user.id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)
    
    db.session.commit()
    flash(f'{product.name} added to cart!', 'success')
    return redirect(request.referrer or url_for('products'))

@app.route('/remove_from_cart/<int:cart_item_id>', methods=['POST'])
@login_required
def remove_from_cart(cart_item_id):
    cart_item = CartItem.query.get_or_404(cart_item_id)
    if cart_item.user_id == current_user.id:
        db.session.delete(cart_item)
        db.session.commit()
        flash('Item removed from cart', 'info')
    return redirect(url_for('cart'))

@app.route('/update_cart/<int:cart_item_id>', methods=['POST'])
@login_required
def update_cart(cart_item_id):
    cart_item = CartItem.query.get_or_404(cart_item_id)
    if cart_item.user_id == current_user.id:
        quantity = int(request.form.get('quantity', 1))
        if quantity > 0:
            cart_item.quantity = quantity
            db.session.commit()
        else:
            db.session.delete(cart_item)
            db.session.commit()
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    
    if not cart_items:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('cart'))
    
    total = sum(item.product.price * item.quantity for item in cart_items)
    
    if request.method == 'POST':
        shipping_address = request.form.get('shipping_address')
        
        # Create order
        order = Order(
            user_id=current_user.id,
            total_amount=total,
            shipping_address=shipping_address,
            status='pending'
        )
        db.session.add(order)
        db.session.flush()
        
        # Create order items
        for cart_item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=cart_item.product_id,
                quantity=cart_item.quantity,
                price=cart_item.product.price
            )
            db.session.add(order_item)
        
        db.session.commit()
        
        # Create Stripe payment intent if Stripe is enabled
        if STRIPE_ENABLED:
            try:
                intent = stripe.PaymentIntent.create(
                    amount=int(total * 100),  # Convert to cents
                    currency='usd',
                    metadata={'order_id': order.id}
                )
                order.stripe_payment_intent_id = intent.id
                db.session.commit()
                
                return render_template('checkout.html', 
                                     order=order, 
                                     cart_items=cart_items,
                                     total=total,
                                     client_secret=intent.client_secret,
                                     stripe_publishable_key=STRIPE_PUBLISHABLE_KEY,
                                     stripe_enabled=True,
                                     razorpay_key_id=RAZORPAY_KEY_ID if RAZORPAY_ENABLED else '',
                                     razorpay_enabled=RAZORPAY_ENABLED)
            except Exception as e:
                flash(f'Payment error: {str(e)}. Using mock payment instead.', 'warning')
                # Fall through to mock payment
        else:
            # Try creating Razorpay order if Razorpay is enabled
            razorpay_order_id = None
            razorpay_success = False
            if RAZORPAY_ENABLED and razorpay_client:
                try:
                    razorpay_order = razorpay_client.order.create({
                        'amount': int(total * 100),  # Convert to paise
                        'currency': 'INR',
                        'receipt': f'order_{order.id}'
                    })
                    razorpay_order_id = razorpay_order['id']
                    order.razorpay_order_id = razorpay_order_id
                    order.payment_method = 'razorpay'
                    db.session.commit()
                    razorpay_success = True
                except Exception as e:
                    print(f"Razorpay order creation fallback: {e}")
                    razorpay_success = False

            # Render checkout with payment options
            return render_template('checkout.html', 
                                 order=order, 
                                 cart_items=cart_items,
                                 total=total,
                                 stripe_publishable_key='',
                                 stripe_enabled=False,
                                 razorpay_order_id=razorpay_order_id,
                                 razorpay_key_id=RAZORPAY_KEY_ID if razorpay_success else '',
                                 razorpay_enabled=razorpay_success)
    
    return render_template('checkout.html', 
                         cart_items=cart_items, 
                         total=total,
                         stripe_publishable_key=STRIPE_PUBLISHABLE_KEY if STRIPE_ENABLED else '',
                         stripe_enabled=STRIPE_ENABLED,
                         razorpay_key_id=RAZORPAY_KEY_ID if RAZORPAY_ENABLED else '',
                         razorpay_enabled=RAZORPAY_ENABLED)

@app.route('/create_razorpay_order', methods=['POST'])
@login_required
def create_razorpay_order():
    """Create Razorpay order"""
    if not RAZORPAY_ENABLED:
        return jsonify({'error': 'Razorpay not configured'}), 400
    
    data = request.get_json()
    order_id = data.get('order_id')
    amount = data.get('amount')
    
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Create Razorpay order (amount in paise, so multiply by 100)
        razorpay_order = razorpay_client.order.create({
            'amount': int(amount * 100),  # Convert to paise
            'currency': 'INR',
            'receipt': f'order_{order.id}',
            'notes': {
                'order_id': order.id,
                'user_id': current_user.id
            }
        })
        
        # Save Razorpay order ID
        order.razorpay_order_id = razorpay_order['id']
        order.payment_method = 'razorpay'
        db.session.commit()
        
        return jsonify({
            'id': razorpay_order['id'],
            'amount': razorpay_order['amount'],
            'currency': razorpay_order['currency'],
            'key': RAZORPAY_KEY_ID
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/razorpay_payment_success', methods=['POST'])
@login_required
def razorpay_payment_success():
    """Verify and process Razorpay payment"""
    if not RAZORPAY_ENABLED:
        flash('Razorpay not configured', 'error')
        return redirect(url_for('orders'))
    
    data = request.get_json()
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')
    
    # Find order
    order = Order.query.filter_by(razorpay_order_id=razorpay_order_id).first()
    if not order or order.user_id != current_user.id:
        flash('Order not found', 'error')
        return redirect(url_for('orders'))
    
    # Verify signature
    try:
        message = f"{razorpay_order_id}|{razorpay_payment_id}"
        generated_signature = hmac.new(
            RAZORPAY_KEY_SECRET.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if generated_signature != razorpay_signature:
            flash('Payment verification failed', 'error')
            return redirect(url_for('orders'))
        
        # Verify payment with Razorpay
        payment = razorpay_client.payment.fetch(razorpay_payment_id)
        
        if payment['status'] == 'authorized' or payment['status'] == 'captured':
            # Mark payment as completed
            order.payment_status = 'completed'
            order.status = 'processing'
            order.razorpay_payment_id = razorpay_payment_id
            
            # Clear cart
            CartItem.query.filter_by(user_id=current_user.id).delete()
            db.session.commit()
            
            flash('Payment successful! Your order is being processed.', 'success')
            return jsonify({'success': True, 'order_id': order.id})
        else:
            flash('Payment failed', 'error')
            return jsonify({'success': False, 'error': 'Payment not successful'}), 400
            
    except Exception as e:
        flash(f'Payment verification error: {str(e)}', 'error')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/mock_payment/<int:order_id>', methods=['POST'])
@login_required
def mock_payment(order_id):
    """Mock payment route for testing when payment gateways are not configured"""
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('orders'))
    
    # Mark payment as completed
    order.payment_status = 'completed'
    order.status = 'processing'
    order.payment_method = 'mock'
    
    # Clear cart
    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    
    flash('Mock payment successful! Your order is being processed.', 'success')
    return redirect(url_for('order_detail', order_id=order.id))

@app.route('/payment_success')
@login_required
def payment_success():
    payment_intent_id = request.args.get('payment_intent')
    
    if payment_intent_id:
        # Check for mock payments
        if payment_intent_id.startswith('mock_'):
            order_id = int(payment_intent_id.split('_')[1])
            order = Order.query.get(order_id)
        else:
            # Real Stripe payment
            order = Order.query.filter_by(stripe_payment_intent_id=payment_intent_id).first()
        
        if order and order.user_id == current_user.id:
            order.payment_status = 'completed'
            order.status = 'processing'
            
            # Clear cart
            CartItem.query.filter_by(user_id=current_user.id).delete()
            db.session.commit()
            
            flash('Payment successful! Your order is being processed.', 'success')
            return redirect(url_for('order_detail', order_id=order.id))
    
    flash('Payment verification failed', 'error')
    return redirect(url_for('index'))

@app.route('/orders')
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=user_orders)

@app.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('orders'))
    return render_template('order_detail.html', order=order)

# Admin routes (optional - for managing products)
@app.route('/admin/products')
@login_required
def admin_products():
    # Simple admin check (in production, use proper role-based access)
    if current_user.username != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    products = Product.query.all()
    return render_template('admin_products.html', products=products)

@app.route('/admin/product/add', methods=['GET', 'POST'])
@login_required
def admin_add_product():
    if current_user.username != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        product = Product(
            name=request.form.get('name'),
            description=request.form.get('description'),
            price=float(request.form.get('price')),
            stock=int(request.form.get('stock', 0)),
            category=request.form.get('category'),
            image_url=request.form.get('image_url', 'https://via.placeholder.com/400')
        )
        db.session.add(product)
        db.session.commit()
        flash('Product added successfully', 'success')
        return redirect(url_for('admin_products'))
    
    return render_template('admin_add_product.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Create sample products if database is empty
        if Product.query.count() == 0:
            sample_products = [
                Product(name='MacBook Pro 16"', description='Powerful laptop with M3 chip, 16GB RAM, 512GB SSD. Perfect for professionals and creatives.', price=2499.99, stock=15, category='Electronics', image_url='https://via.placeholder.com/800x600/2563eb/ffffff?text=MacBook+Pro+16'),
                Product(name='Wireless Gaming Mouse', description='Ergonomic wireless mouse with 12,000 DPI sensor, RGB lighting, and 50-hour battery life.', price=79.99, stock=50, category='Electronics', image_url='https://via.placeholder.com/800x600/7c3aed/ffffff?text=Gaming+Mouse'),
                Product(name='Mechanical RGB Keyboard', description='Full RGB mechanical gaming keyboard with Cherry MX switches and aluminum frame.', price=149.99, stock=30, category='Electronics', image_url='https://via.placeholder.com/800x600/a855f7/ffffff?text=RGB+Keyboard'),
                Product(name='Premium Gaming Headset', description='7.1 Surround sound wireless gaming headset with noise cancellation and RGB lighting.', price=199.99, stock=25, category='Electronics', image_url='https://via.placeholder.com/800x600/ec4899/ffffff?text=Gaming+Headset'),
                Product(name='Apple Watch Series 9', description='Latest smartwatch with fitness tracking, ECG, blood oxygen monitoring, and always-on display.', price=399.99, stock=20, category='Electronics', image_url='https://via.placeholder.com/800x600/10b981/ffffff?text=Apple+Watch'),
                Product(name='USB-C Multi-Port Hub', description='7-in-1 USB-C hub with HDMI, USB 3.0 ports, SD card reader, and power delivery.', price=89.99, stock=40, category='Accessories', image_url='https://via.placeholder.com/800x600/64748b/ffffff?text=USB-C+Hub'),
                Product(name='Ergonomic Laptop Stand', description='Adjustable aluminum laptop stand with ventilation slots and cable management.', price=59.99, stock=35, category='Accessories', image_url='https://via.placeholder.com/800x600/475569/ffffff?text=Laptop+Stand'),
                Product(name='4K Webcam Pro', description='1080p HD webcam with auto-focus, noise cancellation, and privacy shutter.', price=129.99, stock=20, category='Electronics', image_url='https://via.placeholder.com/800x600/fbbf24/ffffff?text=4K+Webcam'),
                Product(name='Wireless Earbuds Pro', description='Premium wireless earbuds with active noise cancellation and 30-hour battery life.', price=179.99, stock=45, category='Electronics', image_url='https://via.placeholder.com/800x600/f472b6/ffffff?text=Wireless+Earbuds'),
                Product(name='Portable SSD 1TB', description='Ultra-fast external SSD with USB-C connectivity, perfect for backups and file transfers.', price=129.99, stock=30, category='Accessories', image_url='https://via.placeholder.com/800x600/334155/ffffff?text=Portable+SSD'),
                Product(name='Monitor 27" 4K', description='27-inch 4K UHD monitor with HDR, 144Hz refresh rate, and USB-C connectivity.', price=449.99, stock=12, category='Electronics', image_url='https://via.placeholder.com/800x600/f59e0b/ffffff?text=4K+Monitor'),
                Product(name='Mechanical Keyboard TKL', description='Tenkeyless mechanical keyboard with RGB backlighting and premium keycaps.', price=119.99, stock=28, category='Electronics', image_url='https://via.placeholder.com/800x600/9333ea/ffffff?text=Keyboard+TKL'),
            ]
            for product in sample_products:
                db.session.add(product)
            db.session.commit()
            print("Sample products created!")
    
    app.run(debug=True)

