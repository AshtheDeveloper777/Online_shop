from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from supabase import create_client
import os
import uuid
import stripe
import razorpay
import hmac
import hashlib
from datetime import datetime
from sqlalchemy import text

load_dotenv()

app = Flask(__name__)

# ========================
# BASIC CONFIG
# ========================
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "change-this-in-production")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///shop.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["REMEMBER_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("FLASK_ENV") == "production"
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_MB", "5")) * 1024 * 1024

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

# ========================
# USER MODEL
# ========================
class User(UserMixin, db.Model):
    __tablename__ = "users"  # match existing Postgres table name
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    # Map ORM attribute 'password_hash' to existing DB column 'password'
    password_hash = db.Column("password", db.String(255), nullable=False)


# ========================
# PRODUCT MODEL
# ========================
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
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    product = db.relationship("Product", backref="cart_items")


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="pending")
    shipping_address = db.Column(db.Text, nullable=True)
    payment_status = db.Column(db.String(20), default="pending")
    payment_method = db.Column(db.String(20), default="mock")
    razorpay_order_id = db.Column(db.String(255), nullable=True)
    razorpay_payment_id = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship("OrderItem", backref="order", lazy=True, cascade="all, delete-orphan")


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    product = db.relationship("Product", backref="order_items")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.context_processor
def inject_cart_meta():
    """Expose lightweight cart stats to all templates."""
    cart_count = 0
    if current_user.is_authenticated:
        cart_count = (
            db.session.query(db.func.coalesce(db.func.sum(CartItem.quantity), 0))
            .filter(CartItem.user_id == current_user.id)
            .scalar()
            or 0
        )
    return {"cart_count": int(cart_count)}


@app.before_request
def bind_request_id():
    request.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())


@app.after_request
def set_security_headers(response):
    response.headers["X-Request-ID"] = getattr(request, "request_id", "")
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if os.getenv("FLASK_ENV") == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    return response


@app.errorhandler(413)
def payload_too_large(_):
    return jsonify({"error": "Upload too large", "request_id": getattr(request, "request_id", "")}), 413


@app.errorhandler(500)
def internal_error(_):
    return jsonify({"error": "Internal server error", "request_id": getattr(request, "request_id", "")}), 500

# ========================
# SUPABASE CONFIG
# ========================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ========================
# RAZORPAY CONFIG
# ========================
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_ENABLED = bool(
    RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET and RAZORPAY_KEY_ID.startswith("rzp_")
)
razorpay_client = None
if RAZORPAY_ENABLED:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# ========================
# HOME ROUTE
# ========================
@app.route("/")
def index():
    products = Product.query.limit(8).all()
    return render_template("index.html", products=products)

# ========================
# REGISTER ROUTE
# ========================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email")
        password = generate_password_hash(request.form.get("password"))

        if User.query.filter_by(username=username).first():
            flash("Username already exists!")
            return redirect(url_for("register"))
        if User.query.filter_by(email=email).first():
            flash("Email already exists!")
            return redirect(url_for("register"))

        new_user = User(username=username, email=email, password_hash=password)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful!")
        return redirect(url_for("login"))

    return render_template("register.html")

# ========================
# LOGIN ROUTE
# ========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        # Safeguard: only check password if a hash is stored
        if user and user.password_hash and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("index"))

        flash("Invalid credentials!")

    return render_template("login.html")
# ========================
# PRODUCTS ROUTE (list)
# ========================
@app.route("/products")
def products():
    category = request.args.get("category")
    search = request.args.get("search")
    query = Product.query
    if category:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(
            Product.name.contains(search) | Product.description.contains(search)
        )
    products = query.all()
    categories = [c[0] for c in db.session.query(Product.category).distinct().all() if c[0]]
    return render_template(
        "Products.html",
        products=products,
        categories=categories,
        current_category=category,
    )


# ========================
# PRODUCT DETAIL ROUTE (single product)
# ========================
@app.route("/product/<int:product_id>")
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template("product_detail.html", product=product)

# ========================
# LOGOUT ROUTE
# ========================
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


# ========================
# CART ROUTES
# ========================
@app.route("/cart")
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template("cart.html", cart_items=cart_items, total=total)


@app.route("/add_to_cart/<int:product_id>", methods=["POST"])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get("quantity", 1))
    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(user_id=current_user.id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)
    db.session.commit()
    flash(f"{product.name} added to cart!", "success")
    return redirect(request.referrer or url_for("products"))


@app.route("/update_cart/<int:cart_item_id>", methods=["POST"])
@login_required
def update_cart(cart_item_id):
    cart_item = CartItem.query.get_or_404(cart_item_id)
    if cart_item.user_id == current_user.id:
        quantity = int(request.form.get("quantity", 1))
        if quantity > 0:
            cart_item.quantity = quantity
            db.session.commit()
        else:
            db.session.delete(cart_item)
            db.session.commit()
    return redirect(url_for("cart"))


@app.route("/remove_from_cart/<int:cart_item_id>", methods=["POST"])
@login_required
def remove_from_cart(cart_item_id):
    cart_item = CartItem.query.get_or_404(cart_item_id)
    if cart_item.user_id == current_user.id:
        db.session.delete(cart_item)
        db.session.commit()
        flash("Item removed from cart", "info")
    return redirect(url_for("cart"))


# ========================
# CHECKOUT & ORDERS
# ========================
@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash("Your cart is empty", "warning")
        return redirect(url_for("cart"))
    total = sum(item.product.price * item.quantity for item in cart_items)

    if request.method == "POST":
        shipping_address = request.form.get("shipping_address")
        order = Order(
            user_id=current_user.id,
            total_amount=total,
            shipping_address=shipping_address,
            status="pending",
        )
        db.session.add(order)
        db.session.flush()
        for cart_item in cart_items:
            db.session.add(
                OrderItem(
                    order_id=order.id,
                    product_id=cart_item.product_id,
                    quantity=cart_item.quantity,
                    price=cart_item.product.price,
                )
            )
        razorpay_order_id = None
        razorpay_amount_paise = None
        if RAZORPAY_ENABLED and razorpay_client:
            try:
                amount_paise = int(round(total * 100))  # INR paise (or cents if you use USD)
                rz_order = razorpay_client.order.create(
                    data={
                        "amount": amount_paise,
                        "currency": "INR",
                        "receipt": f"order_{order.id}",
                    }
                )
                razorpay_order_id = rz_order["id"]
                razorpay_amount_paise = amount_paise
                order.razorpay_order_id = razorpay_order_id
            except Exception as e:
                flash(f"Razorpay error: {str(e)}. You can place order with mock payment.", "warning")
        db.session.commit()

        return render_template(
            "checkout.html",
            order=order,
            cart_items=cart_items,
            total=total,
            stripe_publishable_key="",
            stripe_enabled=False,
            razorpay_key_id=RAZORPAY_KEY_ID,
            razorpay_enabled=RAZORPAY_ENABLED,
            razorpay_order_id=razorpay_order_id,
            razorpay_amount=razorpay_amount_paise,
            razorpay_currency="INR",
            client_secret=None,
        )

    return render_template(
        "checkout.html",
        cart_items=cart_items,
        total=total,
        order=None,
        stripe_publishable_key="",
        stripe_enabled=False,
        razorpay_key_id=RAZORPAY_KEY_ID,
        razorpay_enabled=RAZORPAY_ENABLED,
        client_secret=None,
        razorpay_order_id=None,
        razorpay_amount=None,
        razorpay_currency="INR",
    )


@app.route("/razorpay_payment_success", methods=["POST"])
@login_required
def razorpay_payment_success():
    """Verify Razorpay payment and complete order."""
    if not RAZORPAY_ENABLED or not razorpay_client:
        return jsonify({"success": False, "error": "Razorpay not configured"}), 400
    data = request.get_json() or {}
    razorpay_order_id = data.get("razorpay_order_id")
    razorpay_payment_id = data.get("razorpay_payment_id")
    razorpay_signature = data.get("razorpay_signature")
    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        return jsonify({"success": False, "error": "Missing payment details"}), 400

    order = Order.query.filter_by(razorpay_order_id=razorpay_order_id).first()
    if not order or order.user_id != current_user.id:
        return jsonify({"success": False, "error": "Order not found or access denied"}), 403

    try:
        razorpay_client.utility.verify_payment_signature(
            {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": "Invalid payment signature"}), 400

    order.payment_status = "completed"
    order.status = "processing"
    order.payment_method = "razorpay"
    order.razorpay_payment_id = razorpay_payment_id
    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({"success": True})


@app.route("/mock_payment/<int:order_id>", methods=["POST"])
@login_required
def mock_payment(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash("Access denied", "error")
        return redirect(url_for("orders"))
    order.payment_status = "completed"
    order.status = "processing"
    order.payment_method = "mock"
    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash("Order placed successfully!", "success")
    return redirect(url_for("orders"))


@app.route("/orders")
@login_required
def orders():
    user_orders = (
        Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    )
    return render_template("orders.html", orders=user_orders)


@app.route("/order/<int:order_id>")
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash("Access denied", "error")
        return redirect(url_for("orders"))
    return render_template("order_detail.html", order=order)


# ========================
# FILE UPLOAD ROUTE
# ========================
@app.route("/upload", methods=["POST"])
def upload_file():
    if not supabase:
        return jsonify({"error": "Storage not configured"}), 500

    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file provided"}), 400

    filename = file.filename
    file_bytes = file.read()

    try:
        supabase.storage.from_("uploads").upload(filename, file_bytes)
        public_url = supabase.storage.from_("uploads").get_public_url(filename)

        return jsonify({
            "message": "File uploaded successfully",
            "url": public_url
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========================
# JSON API FOR REACT FRONTEND
# ========================
def _product_to_dict(product):
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description or "",
        "price": float(product.price),
        "image_url": product.image_url or "",
        "stock": int(product.stock or 0),
        "category": product.category or "General",
    }


def _cart_item_to_dict(item):
    return {
        "id": item.id,
        "quantity": item.quantity,
        "product": _product_to_dict(item.product),
        "line_total": float(item.product.price * item.quantity),
    }


def _order_to_dict(order):
    return {
        "id": order.id,
        "total_amount": float(order.total_amount),
        "status": order.status,
        "payment_status": order.payment_status,
        "payment_method": order.payment_method,
        "shipping_address": order.shipping_address or "",
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "items": [
            {
                "id": item.id,
                "quantity": item.quantity,
                "price": float(item.price),
                "product": _product_to_dict(item.product),
            }
            for item in order.items
        ],
    }


@app.route("/api/health")
def api_health():
    db_ok = True
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return jsonify({"ok": True, "service": "online-shop-api", "database_ok": db_ok})


@app.route("/api/auth/me")
def api_auth_me():
    if not current_user.is_authenticated:
        return jsonify({"authenticated": False, "user": None})
    return jsonify(
        {
            "authenticated": True,
            "user": {
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email,
            },
        }
    )


@app.route("/api/auth/register", methods=["POST"])
def api_auth_register():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not username or not email or len(password) < 6:
        return jsonify({"error": "Invalid payload. Password must be at least 6 characters."}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 409
    user = User(username=username, email=email, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return jsonify({"message": "Registered successfully"})


@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    data = request.get_json() or {}
    username = data.get("username") or ""
    password = data.get("password") or ""
    user = User.query.filter_by(username=username).first()
    if not user or not user.password_hash or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid credentials"}), 401
    login_user(user)
    return jsonify({"message": "Logged in successfully"})


@app.route("/api/auth/logout", methods=["POST"])
@login_required
def api_auth_logout():
    logout_user()
    return jsonify({"message": "Logged out successfully"})


@app.route("/api/products")
def api_products():
    category = request.args.get("category")
    search = (request.args.get("search") or "").strip()
    sort = request.args.get("sort", "newest")
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 12)), 1), 50)
    query = Product.query
    if category:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(Product.name.contains(search) | Product.description.contains(search))
    if sort == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    else:
        query = query.order_by(Product.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    products = pagination.items
    categories = [c[0] for c in db.session.query(Product.category).distinct().all() if c[0]]
    return jsonify(
        {
            "products": [_product_to_dict(product) for product in products],
            "categories": categories,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "pages": pagination.pages,
                "total": pagination.total,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
        }
    )


@app.route("/api/products/<int:product_id>")
def api_product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify({"product": _product_to_dict(product)})


@app.route("/api/cart")
@login_required
def api_cart():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    payload = [_cart_item_to_dict(item) for item in items]
    total = sum(item["line_total"] for item in payload)
    return jsonify({"items": payload, "total": total})


@app.route("/api/cart", methods=["POST"])
@login_required
def api_add_to_cart():
    data = request.get_json() or {}
    product_id = data.get("product_id")
    quantity = int(data.get("quantity", 1))
    if not product_id or quantity < 1:
        return jsonify({"error": "Invalid product or quantity"}), 400
    product = Product.query.get_or_404(product_id)
    if product.stock < quantity:
        return jsonify({"error": "Not enough stock available"}), 400
    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if cart_item:
        if product.stock < (cart_item.quantity + quantity):
            return jsonify({"error": "Requested quantity exceeds available stock"}), 400
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(user_id=current_user.id, product_id=product.id, quantity=quantity)
        db.session.add(cart_item)
    db.session.commit()
    return jsonify({"message": f"{product.name} added to cart"})


@app.route("/api/cart/<int:cart_item_id>", methods=["PATCH"])
@login_required
def api_update_cart(cart_item_id):
    item = CartItem.query.get_or_404(cart_item_id)
    if item.user_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json() or {}
    quantity = int(data.get("quantity", 1))
    if quantity < 1:
        db.session.delete(item)
    else:
        if item.product.stock < quantity:
            return jsonify({"error": "Requested quantity exceeds available stock"}), 400
        item.quantity = quantity
    db.session.commit()
    return jsonify({"message": "Cart updated"})


@app.route("/api/cart/<int:cart_item_id>", methods=["DELETE"])
@login_required
def api_remove_cart_item(cart_item_id):
    item = CartItem.query.get_or_404(cart_item_id)
    if item.user_id != current_user.id:
        return jsonify({"error": "Forbidden"}), 403
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Item removed"})


@app.route("/api/checkout", methods=["POST"])
@login_required
def api_checkout():
    data = request.get_json() or {}
    shipping_address = (data.get("shipping_address") or "").strip()
    if not shipping_address:
        return jsonify({"error": "Shipping address is required"}), 400
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        return jsonify({"error": "Cart is empty"}), 400
    total = sum(item.product.price * item.quantity for item in cart_items)
    for item in cart_items:
        if item.product.stock < item.quantity:
            return jsonify({"error": f"Insufficient stock for {item.product.name}"}), 400
    order = Order(
        user_id=current_user.id,
        total_amount=total,
        shipping_address=shipping_address,
        status="processing",
        payment_status="completed",
        payment_method="mock",
    )
    db.session.add(order)
    db.session.flush()
    for cart_item in cart_items:
        cart_item.product.stock -= cart_item.quantity
        db.session.add(
            OrderItem(
                order_id=order.id,
                product_id=cart_item.product_id,
                quantity=cart_item.quantity,
                price=cart_item.product.price,
            )
        )
    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({"message": "Order placed", "order": _order_to_dict(order)})


@app.route("/api/orders")
@login_required
def api_orders():
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return jsonify({"orders": [_order_to_dict(order) for order in user_orders]})


# ========================
# REACT APP SERVING
# ========================
REACT_DIST_DIR = os.path.join(app.root_path, "frontend", "dist")
REACT_ASSETS_DIR = os.path.join(REACT_DIST_DIR, "assets")


@app.route("/app")
@app.route("/app/<path:path>")
def react_app(path="index.html"):
    if not os.path.isdir(REACT_DIST_DIR):
        return (
            "React frontend is not built yet. Run `npm install && npm run build` inside `frontend/`.",
            503,
        )
    target_path = os.path.join(REACT_DIST_DIR, path)
    if path and os.path.exists(target_path):
        return send_from_directory(REACT_DIST_DIR, path)
    return send_from_directory(REACT_DIST_DIR, "index.html")


@app.route("/assets/<path:path>")
def react_assets(path):
    if not os.path.isdir(REACT_ASSETS_DIR):
        return "Frontend assets directory not found.", 404
    return send_from_directory(REACT_ASSETS_DIR, path)


# ========================
# RUN APP
# ========================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        if Product.query.count() == 0:
            db.session.add_all(
                [
                    Product(name="Premium Headphones", description="Wireless ANC headphones.", price=149.99, stock=50, category="Electronics"),
                    Product(name="Smart Watch", description="Health tracking and notifications.", price=199.99, stock=35, category="Electronics"),
                    Product(name="Minimal Backpack", description="Water-resistant urban backpack.", price=89.99, stock=40, category="Fashion"),
                    Product(name="Coffee Beans", description="Single-origin medium roast.", price=17.50, stock=100, category="Grocery"),
                ]
            )
            db.session.commit()

    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)