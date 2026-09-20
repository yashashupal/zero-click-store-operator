from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from .seed import seed_database
from .models import Product, Order, OrderItem
from .schemas import ChatRequest, ChatResponse, ParsedOrder, OrderOut, OrderItemOut
from .ai_parser import parse_order
from .services import create_order

app = FastAPI(title="Zero-Click Store Operator API", version="1.0.0")
origins = [x.strip() for x in settings.cors_origins.split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    seed_database()

def order_to_schema(order):
    return OrderOut(
        id=order.id,
        customer_name=order.customer_name,
        original_request=order.original_request,
        status=order.status,
        total=order.total,
        created_at=order.created_at,
        items=[OrderItemOut(product_name=i.product_name, quantity=i.quantity, unit_price=i.unit_price, subtotal=i.subtotal) for i in order.items],
    )

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "zero-click-store-operator"}

@app.get("/api/products")
def products(db: Session = Depends(get_db)):
    rows = db.query(Product).order_by(Product.category, Product.name).all()
    return [{"id": p.id, "name": p.name, "sku": p.sku, "price": p.price, "stock": p.stock, "category": p.category, "unit": p.unit} for p in rows]

@app.get("/api/orders")
def orders(db: Session = Depends(get_db)):
    rows = db.query(Order).order_by(Order.id.desc()).all()
    return [order_to_schema(o).model_dump(mode="json") for o in rows]

@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    orders = db.query(Order).all()
    return {
        "total_products": len(products),
        "total_orders": len(orders),
        "total_revenue": round(sum(o.total for o in orders), 2),
        "low_stock": sum(1 for p in products if p.stock <= 5),
        "out_of_stock": sum(1 for p in products if p.stock == 0),
        "pending_like": sum(1 for o in orders if o.status != "CANCELLED"),
    }

@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    parsed = parse_order(payload.message)
    order, warnings = create_order(db, payload.customer_name, payload.message, parsed)
    if warnings:
        return ChatResponse(ok=False, message="Order was not created. " + " | ".join(warnings), parsed=parsed, warnings=warnings)
    lines = [f"Order #{order.id} confirmed", ""]
    for item in order.items:
        lines.append(f"{item.quantity} x {item.product_name} = ₹{item.subtotal:.2f}")
    lines.append(f"Total: ₹{order.total:.2f}")
    lines.append("Inventory updated automatically.")
    return ChatResponse(ok=True, message="\n".join(lines), parsed=parsed, order=order_to_schema(order))

@app.post("/api/reset-demo")
def reset_demo(db: Session = Depends(get_db)):
    from .seed import PRODUCTS

    # Delete order items first because they belong to orders.
    db.query(OrderItem).delete(synchronize_session=False)

    # Delete all previous orders.
    db.query(Order).delete(synchronize_session=False)

    # Restore original demo inventory.
    for p in db.query(Product).all():
        original = next((x[3] for x in PRODUCTS if x[1] == p.sku), None)
        if original is not None:
            p.stock = original

    db.commit()

    return {
        "message": "Demo completely reset.",
        "orders": 0,
        "revenue": 0,
        "inventory_reset": True
    }