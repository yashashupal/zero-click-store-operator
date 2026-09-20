from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .database import get_db, engine, Base

from .config import settings
# from .database import get_db
from .models import Product, Order, OrderItem
from .schemas import (
    ChatRequest,
    ChatResponse,
    ParsedOrder,
    OrderOut,
)
from .ai_parser import parse_order
from .services import create_order
from .agent import run_gemini_agent


app = FastAPI(
    title="Zero-Click Store Operator",
    version="1.0.0"
)

Base.metadata.create_all(bind=engine)

from .seed import seed_database
seed_database()


# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in settings.cors_origins.split(",")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def order_to_schema(order: Order) -> OrderOut:

    return OrderOut(
        id=order.id,
        customer_name=order.customer_name,
        original_request=order.original_request,
        status=order.status,
        total=float(order.total),
        created_at=order.created_at,
        items=[
            {
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "subtotal": float(item.subtotal),
            }
            for item in order.items
        ],
    )


def build_order_message(order: Order | None):

    if not order:
        return "Order was not created."

    lines = [
        f"Order #{order.id} confirmed",
        ""
    ]

    for item in order.items:
        lines.append(
            f"{item.quantity} x {item.product_name} = "
            f"₹{float(item.subtotal):.2f}"
        )

    lines.extend([
        "",
        f"Total: ₹{float(order.total):.2f}",
        "Inventory updated automatically."
    ])

    return "\n".join(lines)


# --------------------------------------------------
# HEALTH
# --------------------------------------------------

@app.get("/api/health")
def health():

    return {
        "status": "ok",
        "service": "zero-click-store-operator"
    }


# --------------------------------------------------
# PRODUCTS
# --------------------------------------------------

@app.get("/api/products")
def products(db: Session = Depends(get_db)):

    return [
        {
            "id": p.id,
            "sku": p.sku,
            "name": p.name,
            "price": float(p.price),
            "stock": p.stock,
            "low_stock": p.stock <= 5,
        }
        for p in db.query(Product).order_by(Product.id).all()
    ]


# --------------------------------------------------
# ORDERS
# --------------------------------------------------

@app.get("/api/orders")
def orders(db: Session = Depends(get_db)):

    return [
        order_to_schema(order)
        for order in (
            db.query(Order)
            .order_by(Order.created_at.desc())
            .all()
        )
    ]


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):

    products_data = db.query(Product).all()
    orders_data = db.query(Order).all()

    revenue = sum(
        float(order.total)
        for order in orders_data
    )

    low_stock = sum(
        1
        for product in products_data
        if product.stock <= 5
    )

    return {
        "products": len(products_data),
        "orders": len(orders_data),
        "revenue": revenue,
        "low_stock": low_stock,
    }


# --------------------------------------------------
# CHAT / AI AGENT
# --------------------------------------------------

@app.post("/api/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Main customer order endpoint.

    First tries the Gemini AI Agent.
    If Gemini fails, uses the deterministic parser.
    """

    # --------------------------------------------------
    # GEMINI AI AGENT
    # --------------------------------------------------

    if settings.gemini_api_key:

        try:

            result = run_gemini_agent(
                db=db,
                customer_message=payload.message,
                customer_name=payload.customer_name,
            )

            message = result.get(
                "response",
                "Order processing completed."
            )

            tool_events = result.get(
                "tool_events",
                []
            )

            # Find successfully created order.
            order_id = None

            for event in tool_events:

                if event.get("tool") != "create_order":
                    continue

                tool_result = event.get(
                    "result",
                    {}
                )

                if tool_result.get("success"):

                    order_id = tool_result.get(
                        "order_id"
                    )

                    break

            order = None

            if order_id is not None:

                order = (
                    db.query(Order)
                    .filter(Order.id == order_id)
                    .first()
                )

            # Build ParsedOrder from actual
            # create_order tool arguments.
            parsed = None

            for event in tool_events:

                if event.get("tool") != "create_order":
                    continue

                args = event.get(
                    "args",
                    {}
                )

                items = args.get(
                    "items",
                    []
                )

                try:

                    parsed = ParsedOrder(
                        items=[
                            {
                                "product": item["product"],
                                "quantity": int(
                                    item["quantity"]
                                )
                            }
                            for item in items
                        ],
                        notes="Parsed by Gemini AI Agent"
                    )

                except Exception:

                    parsed = None

                break

            return ChatResponse(
                ok=True,
                message=message,
                parsed=parsed,
                order=(
                    order_to_schema(order)
                    if order
                    else None
                ),
                warnings=[],
                tool_events=tool_events
            )

        except Exception as e:

            print(
                "Gemini Agent failed, "
                f"using fallback parser: {e}"
            )

    # --------------------------------------------------
    # FALLBACK PARSER
    # --------------------------------------------------

    parsed = parse_order(
        payload.message
    )

    order, warnings = create_order(
        db,
        payload.customer_name,
        payload.message,
        parsed
    )

    return ChatResponse(
        ok=order is not None,
        message=(
            build_order_message(order)
            if order
            else "Order was not created."
        ),
        parsed=parsed,
        order=(
            order_to_schema(order)
            if order
            else None
        ),
        warnings=warnings,
        tool_events=[]
    )


# --------------------------------------------------
# RESET DEMO
# --------------------------------------------------

@app.post("/api/reset-demo")
def reset_demo(
    db: Session = Depends(get_db)
):

    from .seed import PRODUCTS

    # Delete order items first.
    db.query(OrderItem).delete(
        synchronize_session=False
    )

    # Delete all orders.
    db.query(Order).delete(
        synchronize_session=False
    )

    # Restore original inventory.
    for product in db.query(Product).all():

        original = next(
            (
                x[3]
                for x in PRODUCTS
                if x[1] == product.sku
            ),
            None
        )

        if original is not None:
            product.stock = original

    db.commit()

    return {
        "message": "Demo completely reset.",
        "orders": 0,
        "revenue": 0,
        "inventory_reset": True
    }