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

# Initialize DB tables and sample data on serverless startup
with app.app_context():
    try:
        db.create_all()
        if Product.query.count() == 0:
            sample_products = [
                Product(name='MacBook Pro 16"', description='Powerful laptop with M3 chip, 16GB RAM, 512GB SSD.', price=2499.99, stock=15, category='Electronics', image_url='https://via.placeholder.com/800x600/2563eb/ffffff?text=MacBook+Pro+16'),
                Product(name='Wireless Gaming Mouse', description='Ergonomic wireless mouse with 12,000 DPI sensor.', price=79.99, stock=50, category='Electronics', image_url='https://via.placeholder.com/800x600/7c3aed/ffffff?text=Gaming+Mouse'),
                Product(name='Mechanical RGB Keyboard', description='Full RGB mechanical gaming keyboard.', price=149.99, stock=30, category='Electronics', image_url='https://via.placeholder.com/800x600/a855f7/ffffff?text=RGB+Keyboard'),
                Product(name='Premium Gaming Headset', description='7.1 Surround sound wireless gaming headset.', price=199.99, stock=25, category='Electronics', image_url='https://via.placeholder.com/800x600/ec4899/ffffff?text=Gaming+Headset'),
                Product(name='Apple Watch Series 9', description='Latest smartwatch with fitness tracking.', price=399.99, stock=20, category='Electronics', image_url='https://via.placeholder.com/800x600/10b981/ffffff?text=Apple+Watch'),
                Product(name='USB-C Multi-Port Hub', description='7-in-1 USB-C hub with HDMI and USB 3.0.', price=89.99, stock=40, category='Accessories', image_url='https://via.placeholder.com/800x600/64748b/ffffff?text=USB-C+Hub'),
            ]
            for product in sample_products:
                db.session.add(product)
            db.session.commit()
    except Exception as e:
        print(f"DB initialization notice: {e}")

# Vercel serverless entrypoint
app = app
