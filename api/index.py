import sys
import os
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

# Ensure parent directory is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Product

# Initialize DB tables, schema migrations and sample data on serverless startup
with app.app_context():
    try:
        try:
            with db.engine.begin() as conn:
                # User table migrations
                conn.execute(db.text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS username VARCHAR(80);'))
                conn.execute(db.text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS email VARCHAR(120);'))
                conn.execute(db.text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);'))
                conn.execute(db.text('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;'))
                
                # Product table migrations
                conn.execute(db.text('ALTER TABLE "product" ADD COLUMN IF NOT EXISTS name VARCHAR(100);'))
                conn.execute(db.text('ALTER TABLE "product" ADD COLUMN IF NOT EXISTS description TEXT;'))
                conn.execute(db.text('ALTER TABLE "product" ADD COLUMN IF NOT EXISTS price FLOAT;'))
                conn.execute(db.text('ALTER TABLE "product" ADD COLUMN IF NOT EXISTS image_url VARCHAR(255);'))
                conn.execute(db.text('ALTER TABLE "product" ADD COLUMN IF NOT EXISTS stock INTEGER DEFAULT 0;'))
                conn.execute(db.text('ALTER TABLE "product" ADD COLUMN IF NOT EXISTS category VARCHAR(50);'))
                conn.execute(db.text('ALTER TABLE "product" ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;'))

                # Order table migrations
                conn.execute(db.text('ALTER TABLE "order" ADD COLUMN IF NOT EXISTS total_amount FLOAT;'))
                conn.execute(db.text('ALTER TABLE "order" ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT \'pending\';'))
                conn.execute(db.text('ALTER TABLE "order" ADD COLUMN IF NOT EXISTS shipping_address TEXT;'))
                conn.execute(db.text('ALTER TABLE "order" ADD COLUMN IF NOT EXISTS payment_status VARCHAR(20) DEFAULT \'pending\';'))
                conn.execute(db.text('ALTER TABLE "order" ADD COLUMN IF NOT EXISTS payment_method VARCHAR(20) DEFAULT \'mock\';'))
                conn.execute(db.text('ALTER TABLE "order" ADD COLUMN IF NOT EXISTS stripe_payment_intent_id VARCHAR(255);'))
                conn.execute(db.text('ALTER TABLE "order" ADD COLUMN IF NOT EXISTS razorpay_order_id VARCHAR(255);'))
                conn.execute(db.text('ALTER TABLE "order" ADD COLUMN IF NOT EXISTS razorpay_payment_id VARCHAR(255);'))
                conn.execute(db.text('ALTER TABLE "order" ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;'))
        except Exception as mig_err:
            print(f"Schema migration note: {mig_err}")

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
    except Exception as e:
        print(f"DB initialization notice: {e}")

# Vercel serverless entrypoint
app = app
