import ReactDOM from "react-dom/client";
import { useEffect, useState } from "react";

const API = "http://127.0.0.1:8000";

const STEPS = [
["find_product", "Finding products"],
["check_inventory", "Checking live inventory"],
["create_order", "Creating order"],
["update_inventory", "Updating inventory"],
];

function money(value) {
return `\u20B9${Number(value || 0).toLocaleString("en-IN")}`;
}

function App() {
const [products, setProducts] = useState([]);
const [orders, setOrders] = useState([]);
const [dashboard, setDashboard] = useState({
products: 0,
orders: 0,
revenue: 0,
low_stock: 0,
});

const [message, setMessage] = useState("");
const [customerName, setCustomerName] = useState("Yash");
const [loading, setLoading] = useState(false);
const [status, setStatus] = useState("ONLINE");
const [events, setEvents] = useState([]);
const [result, setResult] = useState(null);

async function loadData() {
try {
const productsResponse = await fetch(
`${API}/api/products`
);
const ordersResponse = await fetch(
    `${API}/api/orders`
  );

  const dashboardResponse = await fetch(
    `${API}/api/dashboard`
  );

  const productsData =
    await productsResponse.json();

  const ordersData =
    await ordersResponse.json();

  const dashboardData =
    await dashboardResponse.json();

  setProducts(productsData);
  setOrders(ordersData);
  setDashboard(dashboardData);
  setStatus("ONLINE");
} catch (error) {
  console.error(error);
  setStatus("OFFLINE");
}
}

useEffect(() => {
loadData();
}, []);

async function runAgent() {
if (!message.trim() || loading) {
return;
}
setLoading(true);
setStatus("PROCESSING");
setEvents([]);
setResult(null);

try {
  const response = await fetch(
    `${API}/api/chat`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: message,
        customer_name: customerName,
      }),
    }
  );

  if (!response.ok) {
    throw new Error(
      `Backend error ${response.status}`
    );
  }

  const data = await response.json();

  setResult(data);
  setEvents(data.tool_events || []);

  await loadData();

  setStatus(
    data.ok ? "ONLINE" : "READY"
  );
} catch (error) {
  console.error(error);

  setStatus("ERROR");

  setResult({
    ok: false,
    message:
      "Unable to connect to Store Operator backend.",
  });
} finally {
  setLoading(false);
}
}

async function resetDemo() {
try {
const response = await fetch(
`${API}/api/reset-demo`,
{
method: "POST",
}
);
if (!response.ok) {
    throw new Error("Reset failed");
  }

  setMessage("");
  setEvents([]);
  setResult(null);

  await loadData();
} catch (error) {
  console.error(error);
  setStatus("ERROR");
}
}

function getEvents(tool) {
return events.filter(
(event) => event.tool === tool
);
}

function getDescription(event) {
const result = event.result || {};
if (event.tool === "find_product") {
  if (result.found) {
    return `Found ${result.name}`;
  }

  return (
    result.message ||
    "Product not found"
  );
}

if (event.tool === "check_inventory") {
  if (result.available) {
    return `${result.name}: ${result.available_stock} available`;
  }

  return (
    result.message ||
    "Stock unavailable"
  );
}

if (event.tool === "create_order") {
  if (result.success) {
    return `Order #${result.order_id} created`;
  }

  return (
    result.warnings?.join(", ") ||
    "Order creation failed"
  );
}

if (event.tool === "update_inventory") {
  if (result.success) {
    return `${result.product}: ${result.remaining_stock} remaining`;
  }

  return (
    result.message ||
    "Inventory update failed"
  );
}

return "";
}

const completedSteps = STEPS.filter(
([tool]) => getEvents(tool).length > 0
).length;

return ( <div className="min-h-screen bg-slate-950 text-white"> <div className="mx-auto max-w-7xl px-6 py-8">
<header className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
      <div>
        <div className="text-sm font-bold tracking-[0.3em] text-cyan-400">
          AI KIRANA OPERATING SYSTEM
        </div>

        <h1 className="mt-2 text-4xl font-black">
          Zero-Click Store Operator
        </h1>

        <p className="mt-2 text-slate-400">
          Autonomous AI agent for customer orders,
          inventory and store operations.
        </p>
      </div>

      <div className="flex items-center gap-3">
        <div className="rounded-full border border-slate-700 bg-slate-900 px-4 py-2 text-sm font-bold">
          <span className="mr-2 text-green-400">
            ●
          </span>
          {status}
        </div>

        <button
          onClick={resetDemo}
          className="rounded-xl border border-slate-700 bg-slate-900 px-5 py-3 font-bold hover:bg-slate-800"
        >
          Reset Demo
        </button>
      </div>
    </header>

    <div className="mt-8 grid grid-cols-2 gap-4 md:grid-cols-4">
      <Stat
        title="Products"
        value={dashboard.products}
      />

      <Stat
        title="Orders"
        value={dashboard.orders}
      />

      <Stat
        title="Revenue"
        value={money(dashboard.revenue)}
      />

      <Stat
        title="Low Stock"
        value={dashboard.low_stock}
      />
    </div>

    <div className="mt-8 grid gap-6 lg:grid-cols-2">

      <section className="rounded-3xl border border-slate-800 bg-slate-900 p-6">
        <div className="text-xs font-bold tracking-[0.25em] text-cyan-400">
          CUSTOMER ORDER AGENT
        </div>

        <h2 className="mt-3 text-2xl font-bold">
          Give the store a natural-language order
        </h2>

        <p className="mt-2 text-sm text-slate-400">
          English, Hindi or Hinglish supported.
        </p>

        <label className="mt-6 block text-sm font-bold">
          Customer Name
        </label>

        <input
          value={customerName}
          onChange={(event) =>
            setCustomerName(
              event.target.value
            )
          }
          className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 outline-none focus:border-cyan-400"
        />

        <label className="mt-5 block text-sm font-bold">
          Customer Request
        </label>

        <textarea
          value={message}
          onChange={(event) =>
            setMessage(
              event.target.value
            )
          }
          rows={5}
          placeholder="Bhai 2 atta, 1 oil aur 3 Maggi bhej do"
          className="mt-2 w-full resize-none rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 outline-none focus:border-cyan-400"
        />

        <button
          onClick={runAgent}
          disabled={
            loading ||
            !message.trim()
          }
          className="mt-4 w-full rounded-xl bg-cyan-400 px-5 py-3 font-black text-slate-950 hover:bg-cyan-300 disabled:opacity-40"
        >
          {loading
            ? "Agent Processing..."
            : "Run Agent"}
        </button>
      </section>

      <section className="rounded-3xl border border-slate-800 bg-slate-900 p-6">

        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs font-bold tracking-[0.25em] text-cyan-400">
              AUTONOMOUS AGENT
            </div>

            <h2 className="mt-3 text-2xl font-bold">
              Real Tool Execution
            </h2>

            <p className="mt-2 text-sm text-slate-400">
              Actual Gemini function calls from backend.
            </p>
          </div>

          <div className="rounded-full border border-slate-700 px-3 py-1 text-sm font-bold">
            {completedSteps}/4
          </div>
        </div>

        <div className="mt-6 space-y-3">

          {STEPS.map(
            ([tool, title], index) => {
              const toolEvents =
                getEvents(tool);

              const completed =
                toolEvents.length > 0;

              return (
                <div
                  key={tool}
                  className={`rounded-2xl border p-4 ${
                    completed
                      ? "border-green-500/40 bg-green-500/5"
                      : "border-slate-800 bg-slate-950"
                  }`}
                >
                  <div className="flex gap-4">

                    <div
                      className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl font-black ${
                        completed
                          ? "bg-green-400 text-slate-950"
                          : "bg-slate-800 text-slate-500"
                      }`}
                    >
                      {completed
                        ? "✓"
                        : index + 1}
                    </div>

                    <div className="flex-1">

                      <div className="flex items-center justify-between">
                        <div className="font-bold">
                          {title}
                        </div>

                        <div
                          className={`text-xs font-bold ${
                            completed
                              ? "text-green-400"
                              : "text-slate-500"
                          }`}
                        >
                          {completed
                            ? "COMPLETED"
                            : "WAITING"}
                        </div>
                      </div>

                      {!completed && (
                        <div className="mt-1 text-sm text-slate-500">
                          Waiting for agent
                        </div>
                      )}

                      {completed && (
                        <div className="mt-3 space-y-2">
                          {toolEvents.map(
                            (
                              event,
                              eventIndex
                            ) => (
                              <div
                                key={`${tool}-${eventIndex}`}
                                className="rounded-xl bg-slate-950 p-3"
                              >
                                <div className="text-sm font-semibold">
                                  {getDescription(
                                    event
                                  )}
                                </div>

                                <div className="mt-1 text-xs text-slate-500">
                                  Tool call:{" "}
                                  {event.tool}
                                </div>
                              </div>
                            )
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            }
          )}

        </div>
      </section>
    </div>

    {result && (
      <section
        className={`mt-6 rounded-3xl border p-6 ${
          result.ok
            ? "border-green-500/30 bg-green-500/5"
            : "border-red-500/30 bg-red-500/5"
        }`}
      >
        <div className="text-xs font-bold tracking-[0.25em] text-cyan-400">
          AGENT RESULT
        </div>

        <div className="mt-4 whitespace-pre-line text-lg font-semibold">
          {result.message}
        </div>

        {result.order && (
          <div className="mt-5 grid gap-4 md:grid-cols-3">
            <Info
              title="ORDER"
              value={`#${result.order.id}`}
            />

            <Info
              title="TOTAL"
              value={money(
                result.order.total
              )}
            />

            <Info
              title="STATUS"
              value={
                result.order.status
              }
            />
          </div>
        )}
      </section>
    )}

    <section className="mt-8 rounded-3xl border border-slate-800 bg-slate-900 p-6">
      <div className="text-xs font-bold tracking-[0.25em] text-cyan-400">
        LIVE INVENTORY
      </div>

      <h2 className="mt-3 text-2xl font-bold">
        Store Stock
      </h2>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">

        {products.map((product) => (
          <div
            key={product.id}
            className="rounded-2xl border border-slate-800 bg-slate-950 p-4"
          >
            <div className="font-bold">
              {product.name}
            </div>

            <div className="mt-2 text-sm text-slate-400">
              {money(product.price)}
            </div>

            <div
              className={`mt-4 text-2xl font-black ${
                product.low_stock
                  ? "text-red-400"
                  : "text-white"
              }`}
            >
              {product.stock}
            </div>

            <div className="text-xs text-slate-500">
              units available
            </div>

            {product.low_stock && (
              <div className="mt-2 text-xs font-bold text-red-400">
                LOW STOCK
              </div>
            )}
          </div>
        ))}

      </div>
    </section>

    <section className="mt-8 rounded-3xl border border-slate-800 bg-slate-900 p-6">
      <div className="text-xs font-bold tracking-[0.25em] text-cyan-400">
        RECENT ORDERS
      </div>

      <h2 className="mt-3 text-2xl font-bold">
        Store Order History
      </h2>

      <div className="mt-6 space-y-3">

        {orders.map((order) => (
          <div
            key={order.id}
            className="rounded-2xl border border-slate-800 bg-slate-950 p-5"
          >
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">

              <div>
                <div className="text-lg font-black">
                  Order #{order.id}
                </div>

                <div className="text-sm text-slate-400">
                  {order.customer_name}
                </div>
              </div>

              <div>
                <div className="text-xl font-black">
                  {money(order.total)}
                </div>

                <div className="text-xs font-bold text-green-400">
                  {order.status}
                </div>
              </div>

            </div>

            <div className="mt-4 flex flex-wrap gap-2">

              {order.items.map(
                (item, index) => (
                  <div
                    key={`${order.id}-${index}`}
                    className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-300"
                  >
                    {item.quantity} x{" "}
                    {item.product_name}
                  </div>
                )
              )}

            </div>
          </div>
        ))}

      </div>
    </section>

  </div>
</div>
);
}

function Stat({ title, value }) {
return ( <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5"> <div className="text-xs font-bold tracking-[0.2em] text-slate-500">
{title.toUpperCase()} </div>
<div className="mt-3 text-2xl font-black">
    {value}
  </div>
</div>
);
}

function Info({ title, value }) {
return ( <div className="rounded-xl bg-slate-950 p-4"> <div className="text-xs font-bold text-slate-500">
{title} </div>
<div className="mt-1 text-xl font-black">
    {value}
  </div>
</div>
);
}

ReactDOM.createRoot(
document.getElementById("root")
).render( <App />
);

