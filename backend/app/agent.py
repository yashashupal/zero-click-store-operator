from typing import Any

from google import genai
from google.genai import types
from sqlalchemy.orm import Session

from .config import settings
from .services import find_product, create_order
from .schemas import ParsedOrder, ParsedItem


def find_product_tool(
    db: Session,
    product_name: str
) -> dict[str, Any]:

    product = find_product(db, product_name)

    if not product:
        return {
            "found": False,
            "message": f"Product '{product_name}' was not found."
        }

    return {
        "found": True,
        "product_id": product.id,
        "name": product.name,
        "price": float(product.price),
        "stock": product.stock
    }


def check_inventory_tool(
    db: Session,
    product_name: str,
    quantity: int
) -> dict[str, Any]:

    product = find_product(db, product_name)

    if not product:
        return {
            "available": False,
            "message": f"Product '{product_name}' was not found."
        }

    if quantity <= product.stock:
        return {
            "available": True,
            "product_id": product.id,
            "name": product.name,
            "requested_quantity": quantity,
            "available_stock": product.stock,
            "message": (
                f"{quantity} units of {product.name} are available."
            )
        }

    return {
        "available": False,
        "product_id": product.id,
        "name": product.name,
        "requested_quantity": quantity,
        "available_stock": product.stock,
        "message": (
            f"Insufficient stock for {product.name}: "
            f"requested {quantity}, available {product.stock}"
        )
    }


def create_order_tool(
    db: Session,
    customer_name: str,
    original_request: str,
    items: list[dict[str, Any]]
) -> dict[str, Any]:

    parsed_items = []

    for item in items:
        parsed_items.append(
            ParsedItem(
                product=item["product"],
                quantity=int(item["quantity"])
            )
        )

    parsed = ParsedOrder(
        items=parsed_items,
        notes="Created by Gemini AI Agent"
    )

    order, warnings = create_order(
        db=db,
        customer_name=customer_name,
        original_request=original_request,
        parsed=parsed
    )

    if warnings:
        return {
            "success": False,
            "warnings": warnings
        }

    return {
        "success": True,
        "order_id": order.id,
        "total": float(order.total),
        "status": order.status,
        "message": f"Order #{order.id} created successfully."
    }


def update_inventory_tool(
    db: Session,
    product_name: str,
    quantity: int
) -> dict[str, Any]:

    product = find_product(db, product_name)

    if not product:
        return {
            "success": False,
            "message": f"Product '{product_name}' was not found."
        }

    return {
        "success": True,
        "product_id": product.id,
        "product": product.name,
        "remaining_stock": product.stock,
        "message": (
            f"Inventory verified for {product.name}. "
            f"Remaining stock: {product.stock}"
        )
    }


def run_gemini_agent(
    db: Session,
    customer_message: str,
    customer_name: str = "Walk-in Customer"
) -> dict[str, Any]:

    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    client = genai.Client(
        api_key=settings.gemini_api_key
    )

    tools = [
        types.FunctionDeclaration(
            name="find_product",
            description=(
                "Find a product in the kirana store catalog. "
                "Use this when the customer mentions a product."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "product_name": types.Schema(
                        type=types.Type.STRING,
                        description=(
                            "Product name or common alias."
                        )
                    )
                },
                required=["product_name"]
            )
        ),

        types.FunctionDeclaration(
            name="check_inventory",
            description=(
                "Check whether the requested quantity of a "
                "product is available in current store inventory."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "product_name": types.Schema(
                        type=types.Type.STRING
                    ),
                    "quantity": types.Schema(
                        type=types.Type.INTEGER
                    )
                },
                required=[
                    "product_name",
                    "quantity"
                ]
            )
        ),

        types.FunctionDeclaration(
            name="create_order",
            description=(
                "Create the customer's order after all "
                "products and inventory have been verified."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "customer_name": types.Schema(
                        type=types.Type.STRING
                    ),
                    "original_request": types.Schema(
                        type=types.Type.STRING
                    ),
                    "items": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "product": types.Schema(
                                    type=types.Type.STRING
                                ),
                                "quantity": types.Schema(
                                    type=types.Type.INTEGER
                                )
                            },
                            required=[
                                "product",
                                "quantity"
                            ]
                        )
                    )
                },
                required=[
                    "customer_name",
                    "original_request",
                    "items"
                ]
            )
        ),

        types.FunctionDeclaration(
            name="update_inventory",
            description=(
                "Verify inventory after an order has "
                "been created."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "product_name": types.Schema(
                        type=types.Type.STRING
                    ),
                    "quantity": types.Schema(
                        type=types.Type.INTEGER
                    )
                },
                required=[
                    "product_name",
                    "quantity"
                ]
            )
        )
    ]

    tool_config = types.Tool(
        function_declarations=tools
    )

    system_instruction = """
You are an autonomous AI agent operating a small Indian kirana store.

Your job is to process customer orders.

Rules:

1. Understand English, Hindi and Hinglish.
2. Identify every requested product and quantity.
3. Use find_product for each requested product.
4. Use check_inventory before creating an order.
5. Never create an order if requested stock is insufficient.
6. Only create an order after inventory has been checked.
7. Use create_order to create the order.
8. After successful order creation, use update_inventory
   to verify inventory.
9. Never invent products.
10. Common aliases:
   atta -> Aashirvaad Atta
   oil -> Fortune Oil
   maggi -> Maggi
   salt -> Tata Salt
   milk -> Amul Milk
   biscuits -> Parle-G Biscuits
   toothpaste -> Colgate Toothpaste
   surf -> Surf Excel
   coke -> Coca Cola
   bread -> Britannia Bread
11. Quantities must be positive integers.
12. If stock is insufficient, do not create an order.
13. After successful completion, give a concise confirmation
    with order number, items, total and inventory status.
14. Never claim a tool action happened unless the tool
    actually returned a successful result.
"""

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part(
                    text=(
                        f"Customer name: {customer_name}\n"
                        f"Customer request: {customer_message}"
                    )
                )
            ]
        )
    ]

    tool_events = []

    for _ in range(10):

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=[tool_config],
                temperature=0.1
            )
        )

        if not response.candidates:
            raise RuntimeError(
                "Gemini returned no candidates."
            )

        candidate = response.candidates[0]

        # IMPORTANT:
        # Preserve the complete model content, including
        # function calls and thought signatures.
        contents.append(candidate.content)

        function_calls = []

        for part in candidate.content.parts:
            if getattr(part, "function_call", None):
                function_calls.append(part.function_call)

        if not function_calls:
            return {
                "success": True,
                "response": response.text
                or "Order processing completed.",
                "tool_events": tool_events
            }

        function_response_parts = []

        for function_call in function_calls:

            name = function_call.name
            args = dict(function_call.args or {})

            tool_events.append({
                "tool": name,
                "args": args
            })

            if name == "find_product":

                result = find_product_tool(
                    db,
                    args["product_name"]
                )

            elif name == "check_inventory":

                result = check_inventory_tool(
                    db,
                    args["product_name"],
                    int(args["quantity"])
                )

            elif name == "create_order":

                result = create_order_tool(
                    db,
                    args["customer_name"],
                    args["original_request"],
                    args["items"]
                )

            elif name == "update_inventory":

                result = update_inventory_tool(
                    db,
                    args["product_name"],
                    int(args["quantity"])
                )

            else:

                result = {
                    "success": False,
                    "message": f"Unknown tool: {name}"
                }

            tool_events[-1]["result"] = result

            # Correct Gemini Function Calling response format.
            function_response_parts.append(
                types.Part.from_function_response(
                    name=name,
                    response=result
                )
            )

        # IMPORTANT:
        # Function responses must be sent as USER content,
        # not role='tool'.
        contents.append(
            types.Content(
                role="user",
                parts=function_response_parts
            )
        )

    raise RuntimeError(
        "Gemini agent exceeded maximum tool-call steps."
    )