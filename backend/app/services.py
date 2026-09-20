from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from .models import Product, Order, OrderItem
from .schemas import ParsedOrder


def find_product(db: Session, name: str):
    q = name.strip().lower()
    products = db.query(Product).all()
    exact = next((p for p in products if p.name.lower() == q), None)
    if exact:
        return exact
    return next((p for p in products if q in p.name.lower() or p.name.lower() in q), None)


def create_order(db: Session, customer_name: str, original_request: str, parsed: ParsedOrder):
    if not parsed.items:
        return None, ["No supported product was detected. Try: '2 atta and 1 oil'."]
    resolved = []
    warnings = []
    for item in parsed.items:
        product = find_product(db, item.product)
        if not product:
            warnings.append(f"Product not found: {item.product}")
            continue
        if item.quantity > product.stock:
            warnings.append(f"Insufficient stock for {product.name}: requested {item.quantity}, available {product.stock}")
            continue
        resolved.append((product, item.quantity))
    if warnings or not resolved:
        db.rollback()
        return None, warnings or ["No orderable items found."]

    total = sum(product.price * qty for product, qty in resolved)
    order = Order(customer_name=customer_name, original_request=original_request, total=total, status="CONFIRMED")
    db.add(order)
    db.flush()
    for product, qty in resolved:
        subtotal = product.price * qty
        product.stock -= qty
        db.add(OrderItem(order_id=order.id, product_id=product.id, product_name=product.name, quantity=qty, unit_price=product.price, subtotal=subtotal))
    db.commit()
    db.refresh(order)
    return order, []
