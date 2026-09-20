from .database import Base, engine, SessionLocal
from .models import Product

PRODUCTS = [
    ("Aashirvaad Atta", "ATT-001", 300, 20, "Staples", "packet"),
    ("Fortune Oil", "OIL-001", 150, 15, "Cooking Oil", "bottle"),
    ("Maggi", "MAG-001", 15, 50, "Instant Food", "packet"),
    ("Tata Salt", "SAL-001", 28, 30, "Staples", "packet"),
    ("Amul Milk", "MIL-001", 32, 25, "Dairy", "packet"),
    ("Parle-G Biscuits", "BIS-001", 10, 40, "Biscuits", "packet"),
    ("Colgate Toothpaste", "COL-001", 95, 18, "Personal Care", "tube"),
    ("Surf Excel", "SUR-001", 120, 12, "Home Care", "packet"),
    ("Coca Cola", "COC-001", 45, 24, "Beverages", "bottle"),
    ("Britannia Bread", "BRE-001", 40, 16, "Bakery", "packet"),
]

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Product).count() == 0:
            for p in PRODUCTS:
                db.add(Product(name=p[0], sku=p[1], price=p[2], stock=p[3], category=p[4], unit=p[5]))
            db.commit()
    finally:
        db.close()
