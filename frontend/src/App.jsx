import { useEffect, useMemo, useState } from "react";

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
}

function loadRazorpayScript() {
  return new Promise((resolve) => {
    if (window.Razorpay) {
      resolve(true);
      return;
    }
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

function App() {
  const [user, setUser] = useState(null);
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState("");
  const [pagination, setPagination] = useState({ page: 1, per_page: 12, pages: 1, total: 0 });
  const [cart, setCart] = useState({ items: [], total: 0 });
  const [orders, setOrders] = useState([]);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("price_asc");
  const [authForm, setAuthForm] = useState({ username: "", email: "", password: "" });
  const [address, setAddress] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [voiceActive, setVoiceActive] = useState(false);
  const [checkoutStep, setCheckoutStep] = useState(1);
  const [dragOverCart, setDragOverCart] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState("razorpay");
  const [paymentConfig, setPaymentConfig] = useState({ razorpay_enabled: false, razorpay_key_id: "" });

  const loadAll = async (page = 1, query = search, sortBy = sort, category = selectedCategory) => {
    setLoading(true);
    const categoryParam = category ? `&category=${encodeURIComponent(category)}` : "";
    const productUrl = `/api/products?page=${page}&per_page=16&sort=${encodeURIComponent(sortBy)}&search=${encodeURIComponent(query)}${categoryParam}`;
    const [{ products: productList, pagination: pg, categories: cat }, me] = await Promise.all([
      api(productUrl),
      api("/api/auth/me"),
    ]);
    setProducts(productList || []);
    setPagination(pg || { page: 1, per_page: 12, pages: 1, total: 0 });
    setCategories(cat || []);
    if (me.authenticated) {
      setUser(me.user);
      const [cartData, ordersData, payConfig] = await Promise.all([
        api("/api/cart"),
        api("/api/orders"),
        api("/api/payments/config"),
      ]);
      setCart(cartData);
      setOrders(ordersData.orders || []);
      setPaymentConfig(payConfig || { razorpay_enabled: false, razorpay_key_id: "" });
      if (!(payConfig && payConfig.razorpay_enabled)) {
        setPaymentMethod("mock");
      }
    } else {
      setUser(null);
      setCart({ items: [], total: 0 });
      setOrders([]);
      setPaymentConfig({ razorpay_enabled: false, razorpay_key_id: "" });
    }
    setLoading(false);
  };

  useEffect(() => {
    loadAll().catch((err) => setMessage(err.message));
  }, []);

  const handleRegister = async (event) => {
    event.preventDefault();
    await api("/api/auth/register", { method: "POST", body: JSON.stringify(authForm) });
    setMessage("Account created. You are now logged in.");
    await loadAll();
  };

  const handleLogin = async (event) => {
    event.preventDefault();
    await api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username: authForm.username, password: authForm.password }),
    });
    setMessage("Logged in successfully.");
    await loadAll();
  };

  const handleLogout = async () => {
    await api("/api/auth/logout", { method: "POST" });
    setMessage("Logged out.");
    await loadAll();
  };

  const addToCart = async (productId) => {
    await api("/api/cart", { method: "POST", body: JSON.stringify({ product_id: productId, quantity: 1 }) });
    const cartData = await api("/api/cart");
    setCart(cartData);
    setMessage("Item added to cart.");
  };

  const updateQty = async (itemId, quantity) => {
    await api(`/api/cart/${itemId}`, { method: "PATCH", body: JSON.stringify({ quantity }) });
    setCart(await api("/api/cart"));
  };

  const checkout = async (event) => {
    event.preventDefault();
    const checkoutResponse = await api("/api/checkout", {
      method: "POST",
      body: JSON.stringify({
        shipping_address: address,
        payment_method: paymentMethod,
      }),
    });
    if (checkoutResponse.requires_action && checkoutResponse.payment?.provider === "razorpay") {
      const ok = await loadRazorpayScript();
      if (!ok) {
        setMessage("Failed to load Razorpay checkout script.");
        return;
      }
      const payment = checkoutResponse.payment;
      const rzp = new window.Razorpay({
        key: payment.key_id || paymentConfig.razorpay_key_id,
        amount: payment.amount,
        currency: payment.currency,
        name: "NOVA-X COMMERCE",
        description: `Order #${checkoutResponse.order.id}`,
        order_id: payment.order_id,
        handler: async function (response) {
          try {
            await api("/api/payments/razorpay/verify", {
              method: "POST",
              body: JSON.stringify({
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
              }),
            });
            setAddress("");
            setMessage("Razorpay payment successful. Order placed.");
            setCheckoutStep(1);
            await loadAll();
          } catch (err) {
            setMessage(`Payment verification failed: ${err.message}`);
          }
        },
        theme: { color: "#6366F1" },
      });
      rzp.on("payment.failed", function () {
        setMessage("Payment failed. Please try again.");
      });
      rzp.open();
      return;
    }
    setAddress("");
    setMessage("Order placed successfully.");
    setCheckoutStep(1);
    await loadAll();
  };

  const cartCount = cart.items.reduce((acc, item) => acc + item.quantity, 0);
  const cartValue = Number(cart.total || 0);
  const immersivePicks = useMemo(() => products.slice(0, 7), [products]);
  const recs = useMemo(() => [...products].sort((a, b) => b.stock - a.stock).slice(0, 5), [products]);

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_70%_10%,rgba(236,72,153,0.2),transparent_35%),radial-gradient(circle_at_20%_30%,rgba(59,130,246,0.2),transparent_40%)]" />

      <header className="fixed left-1/2 top-4 z-30 w-[min(1200px,94vw)] -translate-x-1/2 rounded-2xl px-4 py-3 glass neon-border">
        <div className="flex flex-wrap items-center gap-3">
          <div className="text-xl font-semibold tracking-wider neon-text">NOVA-X COMMERCE</div>
          <div className="flex flex-1 items-center gap-2">
            <input
              className="w-full rounded-xl border border-indigo-300/30 bg-slate-950/60 px-3 py-2 text-sm outline-none focus:border-cyan-300"
              placeholder="Ask AI to find your next product..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <button
              onClick={() => loadAll(1, search, sort, selectedCategory)}
              className="rounded-xl bg-gradient-to-r from-cyan-400 to-indigo-500 px-4 py-2 text-sm font-medium text-slate-950"
            >
              Explore
            </button>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className="rounded-full border border-cyan-300/40 bg-cyan-400/10 px-3 py-1">{cartCount} items</span>
            <span className="rounded-full border border-fuchsia-300/40 bg-fuchsia-400/10 px-3 py-1">${cartValue.toFixed(2)}</span>
            {user ? (
              <>
                <span className="rounded-full border border-indigo-300/40 bg-indigo-400/10 px-3 py-1">{user.username}</span>
                <button onClick={handleLogout} className="rounded-full border border-slate-300/40 px-3 py-1">Logout</button>
              </>
            ) : (
              <span className="rounded-full border border-slate-300/40 px-3 py-1">Guest</span>
            )}
          </div>
        </div>
      </header>

      <main className="relative z-10 mx-auto flex w-[min(1250px,95vw)] flex-col gap-12 pb-16 pt-28">
        <section className="world-section rounded-3xl p-8 glass">
          <div className="grid gap-8 lg:grid-cols-[1.3fr_0.7fr]">
            <div>
              <p className="mb-3 text-xs uppercase tracking-[0.25em] text-cyan-300">Future Shopping Interface</p>
              <h1 className="max-w-3xl text-4xl font-semibold leading-tight md:text-6xl">
                A cinematic, AI-powered storefront that morphs as you explore
              </h1>
              <p className="mt-5 max-w-2xl text-slate-200/80">
                Scroll through product worlds, interact with floating cards, drag items into the quantum cart,
                and complete checkout as an immersive journey.
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <button className="rounded-xl bg-gradient-to-r from-fuchsia-500 to-indigo-500 px-5 py-2.5 text-sm font-semibold">Enter Discovery World</button>
                <button className="rounded-xl border border-slate-300/30 px-5 py-2.5 text-sm">Launch AR Preview</button>
              </div>
            </div>
            <div className="space-y-3">
              <div className="rounded-2xl border border-indigo-300/30 bg-slate-950/50 p-4">
                <p className="text-xs uppercase text-slate-300">Voice Search</p>
                <button
                  onClick={() => setVoiceActive((v) => !v)}
                  className={`mt-3 w-full rounded-xl px-3 py-2 text-sm ${voiceActive ? "bg-cyan-400 text-slate-900" : "bg-slate-800 text-white"}`}
                >
                  {voiceActive ? "Listening..." : "Start Voice Command"}
                </button>
                <div className="mt-3 flex h-8 items-end gap-1">
                  {[1, 2, 3, 4, 5, 6].map((bar) => (
                    <div
                      key={bar}
                      className={`voice-bar w-2 rounded-full bg-gradient-to-t from-cyan-400 to-fuchsia-400 ${voiceActive ? "opacity-100" : "opacity-40"}`}
                      style={{ height: voiceActive ? 18 + (bar % 3) * 7 : 10 }}
                    />
                  ))}
                </div>
              </div>
              <div className="rounded-2xl border border-fuchsia-300/30 bg-slate-950/50 p-4">
                <p className="text-xs uppercase text-slate-300">AI Assistant Avatar</p>
                <div className="mt-3 flex items-center gap-3">
                  <div className="h-12 w-12 rounded-full bg-gradient-to-br from-cyan-400 to-fuchsia-500" />
                  <p className="text-sm text-slate-200">"I remixed your storefront based on your recent preferences."</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {!user && (
          <section className="grid gap-4 md:grid-cols-2">
            <form className="rounded-2xl p-5 glass" onSubmit={handleRegister}>
              <h2 className="mb-3 text-xl">Create Identity</h2>
              <div className="grid gap-2">
                <input className="rounded-xl border border-indigo-300/30 bg-slate-950/60 px-3 py-2" placeholder="Username" value={authForm.username} onChange={(e) => setAuthForm({ ...authForm, username: e.target.value })} required />
                <input className="rounded-xl border border-indigo-300/30 bg-slate-950/60 px-3 py-2" placeholder="Email" type="email" value={authForm.email} onChange={(e) => setAuthForm({ ...authForm, email: e.target.value })} required />
                <input className="rounded-xl border border-indigo-300/30 bg-slate-950/60 px-3 py-2" placeholder="Password" type="password" value={authForm.password} onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })} required minLength={6} />
                <button className="mt-2 rounded-xl bg-gradient-to-r from-cyan-400 to-indigo-500 px-4 py-2 font-medium text-slate-950">Register</button>
              </div>
            </form>
            <form className="rounded-2xl p-5 glass" onSubmit={handleLogin}>
              <h2 className="mb-3 text-xl">Connect</h2>
              <div className="grid gap-2">
                <input className="rounded-xl border border-indigo-300/30 bg-slate-950/60 px-3 py-2" placeholder="Username" value={authForm.username} onChange={(e) => setAuthForm({ ...authForm, username: e.target.value })} required />
                <input className="rounded-xl border border-indigo-300/30 bg-slate-950/60 px-3 py-2" placeholder="Password" type="password" value={authForm.password} onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })} required />
                <button className="mt-2 rounded-xl bg-gradient-to-r from-fuchsia-400 to-indigo-500 px-4 py-2 font-medium text-slate-950">Login</button>
              </div>
            </form>
          </section>
        )}

        <section className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="rounded-2xl p-5 glass">
            <h3 className="mb-3 text-lg">Radial Navigation</h3>
            <div className="relative mx-auto h-64 w-64">
              <button className="absolute left-1/2 top-1/2 h-16 w-16 -translate-x-1/2 -translate-y-1/2 rounded-full bg-gradient-to-br from-cyan-400 to-fuchsia-500 text-slate-900">AI</button>
              {categories.slice(0, 6).map((cat, idx) => {
                const angle = (idx / Math.max(1, categories.slice(0, 6).length)) * Math.PI * 2;
                const x = Math.cos(angle) * 95;
                const y = Math.sin(angle) * 95;
                return (
                  <button
                    key={cat}
                    onClick={() => {
                      setSelectedCategory(cat);
                      loadAll(1, search, sort, cat);
                    }}
                    className="absolute rounded-full border border-indigo-300/30 bg-slate-900/70 px-3 py-1 text-xs"
                    style={{ left: `calc(50% + ${x}px)`, top: `calc(50% + ${y}px)`, transform: "translate(-50%, -50%)" }}
                  >
                    {cat}
                  </button>
                );
              })}
            </div>
            <div className="mt-3 flex gap-2">
              <select className="flex-1 rounded-xl border border-indigo-300/30 bg-slate-950/60 px-2 py-2 text-sm" value={sort} onChange={(e) => setSort(e.target.value)}>
                <option value="price_asc">Price Low to High</option>
                <option value="price_desc">Price High to Low</option>
                <option value="newest">Newest</option>
              </select>
              <button className="rounded-xl border border-slate-300/30 px-4 text-sm" onClick={() => loadAll(1, search, sort, selectedCategory)}>Refresh</button>
            </div>
          </div>

          <div className="rounded-2xl p-5 glass">
            <h3 className="mb-3 text-lg">Smart Recommendation Carousel</h3>
            <div className="grid gap-3 md:grid-cols-2">
              {recs.map((product) => (
                <article key={product.id} className="float-card rounded-2xl border border-fuchsia-300/20 bg-slate-950/55 p-4">
                  <p className="text-xs uppercase tracking-wide text-cyan-300">{product.category}</p>
                  <h4 className="mt-1 text-lg">{product.name}</h4>
                  <p className="mt-1 text-sm text-slate-300/80">{product.description}</p>
                  <div className="mt-3 flex items-center justify-between">
                    <strong>${product.price.toFixed(2)}</strong>
                    <button
                      draggable
                      onDragStart={(e) => e.dataTransfer.setData("text/plain", String(product.id))}
                      onClick={() => addToCart(product.id)}
                      disabled={!user || product.stock <= 0}
                      className="rounded-xl bg-gradient-to-r from-cyan-400 to-indigo-500 px-3 py-1 text-sm font-medium text-slate-950 disabled:opacity-40"
                    >
                      Drag / Add
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="rounded-2xl p-5 glass">
          <h3 className="mb-3 text-lg">Exploration Stream (Split-screen Storytelling)</h3>
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="space-y-3">
              {immersivePicks.map((product) => (
                <div key={product.id} className="rounded-2xl border border-indigo-300/20 bg-slate-950/45 p-4">
                  <p className="text-xs text-cyan-300">{product.category}</p>
                  <h4>{product.name}</h4>
                  <p className="text-sm text-slate-300/80">{product.description}</p>
                  <div className="mt-2 flex items-center justify-between">
                    <span>${product.price.toFixed(2)}</span>
                    <button
                      onClick={() => addToCart(product.id)}
                      disabled={!user || product.stock <= 0}
                      className="rounded-lg border border-fuchsia-300/35 px-3 py-1 text-xs disabled:opacity-40"
                    >
                      Add
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <div className="rounded-2xl border border-fuchsia-300/25 bg-slate-950/60 p-4">
              <h4 className="text-lg">AR Preview Environment (Mockup)</h4>
              <p className="mt-1 text-sm text-slate-300/80">Simulated view: product appears in your room with real-world scale and lighting.</p>
              <div className="mt-4 grid h-72 place-items-center rounded-2xl border border-cyan-300/20 bg-[radial-gradient(circle_at_50%_35%,rgba(59,130,246,0.35),rgba(2,6,23,0.9))]">
                <div className="h-32 w-32 rounded-2xl border border-fuchsia-300/40 bg-gradient-to-br from-cyan-300/50 to-indigo-500/55 shadow-[0_0_40px_rgba(99,102,241,0.6)]" />
                <span className="text-xs text-slate-300">Gesture-based rotate / resize controls</span>
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <article className="rounded-2xl p-5 glass">
            <h3 className="mb-3 text-lg">Drag-to-Cart Quantum Dock</h3>
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragOverCart(true);
              }}
              onDragLeave={() => setDragOverCart(false)}
              onDrop={async (e) => {
                e.preventDefault();
                setDragOverCart(false);
                const productId = Number(e.dataTransfer.getData("text/plain"));
                if (productId) await addToCart(productId);
              }}
              className={`grid h-32 place-items-center rounded-2xl border-2 border-dashed transition ${dragOverCart ? "border-cyan-300 bg-cyan-400/10" : "border-indigo-300/30 bg-slate-950/40"}`}
            >
              <p className="text-sm text-slate-300">Drop floating product cards here</p>
            </div>
            <div className="mt-4 space-y-2">
              {cart.items.slice(0, 5).map((item) => (
                <div key={item.id} className="grid grid-cols-[1fr_auto_auto] items-center gap-2 rounded-xl border border-slate-300/20 p-2">
                  <span>{item.product.name}</span>
                  <input className="w-16 rounded border border-indigo-300/30 bg-slate-950/55 px-2 py-1" type="number" min="1" value={item.quantity} onChange={(e) => updateQty(item.id, Number(e.target.value))} />
                  <span>${item.line_total.toFixed(2)}</span>
                </div>
              ))}
            </div>
            <p className="mt-3 text-right text-lg font-semibold">Total ${cartValue.toFixed(2)}</p>
          </article>

          <article className="rounded-2xl p-5 glass">
            <h3 className="mb-3 text-lg">Immersive Checkout Journey</h3>
            <div className="mb-4 grid grid-cols-3 gap-2 text-xs">
              {[1, 2, 3].map((step) => (
                <button
                  key={step}
                  type="button"
                  onClick={() => setCheckoutStep(step)}
                  className={`rounded-xl border px-2 py-2 ${checkoutStep === step ? "border-cyan-300 bg-cyan-400/15" : "border-slate-300/25"}`}
                >
                  Step {step}
                </button>
              ))}
            </div>
            <form onSubmit={checkout} className="space-y-3">
              {checkoutStep === 1 && (
                <div className="rounded-xl border border-slate-300/20 p-3 text-sm text-slate-200">Identity verified: {user ? user.username : "guest mode"}.</div>
              )}
              {checkoutStep === 2 && (
                <input
                  className="w-full rounded-xl border border-indigo-300/30 bg-slate-950/55 px-3 py-2"
                  placeholder="Neural delivery address"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  required
                />
              )}
              {checkoutStep === 3 && (
                <div className="space-y-2">
                  <div className="rounded-xl border border-fuchsia-300/20 bg-fuchsia-500/10 p-3 text-sm">
                    Confirm holographic order stream: {cartCount} item(s) | ${cartValue.toFixed(2)}
                  </div>
                  <div className="rounded-xl border border-indigo-300/25 bg-indigo-500/10 p-3 text-sm">
                    <p className="mb-2">Choose payment method</p>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => setPaymentMethod("razorpay")}
                        disabled={!paymentConfig.razorpay_enabled}
                        className={`rounded-lg border px-3 py-1 ${paymentMethod === "razorpay" ? "border-cyan-300 bg-cyan-400/20" : "border-slate-300/30"}`}
                      >
                        Razorpay {paymentConfig.razorpay_enabled ? "" : "(Unavailable)"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setPaymentMethod("mock")}
                        className={`rounded-lg border px-3 py-1 ${paymentMethod === "mock" ? "border-cyan-300 bg-cyan-400/20" : "border-slate-300/30"}`}
                      >
                        Mock payment
                      </button>
                    </div>
                  </div>
                </div>
              )}
              <button
                disabled={!user || cart.items.length === 0 || checkoutStep !== 3}
                className="w-full rounded-xl bg-gradient-to-r from-fuchsia-500 to-indigo-500 px-4 py-2 font-semibold text-slate-950 disabled:opacity-40"
              >
                {paymentMethod === "razorpay" ? "Pay with Razorpay" : "Complete Immersive Checkout"}
              </button>
            </form>
          </article>
        </section>

        <section className="rounded-2xl p-5 glass">
          <h3 className="mb-3 text-lg">Orders Timeline</h3>
          {orders.length === 0 ? (
            <p className="text-sm text-slate-300/80">No orders yet.</p>
          ) : (
            <div className="space-y-2">
              {orders.map((order) => (
                <div key={order.id} className="grid grid-cols-[1fr_auto_auto] items-center gap-3 rounded-xl border border-indigo-300/20 p-3">
                  <div>
                    <p className="text-sm">Order #{order.id}</p>
                    <p className="text-xs text-slate-300/75">{new Date(order.created_at).toLocaleString()}</p>
                  </div>
                  <span className="rounded-full border border-cyan-300/35 bg-cyan-400/10 px-3 py-1 text-xs">{order.status}</span>
                  <strong>${order.total_amount.toFixed(2)}</strong>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>

      <nav className="fixed bottom-6 right-6 z-20 flex flex-col gap-2 rounded-2xl p-3 glass">
        <button className="rounded-full border border-slate-300/30 px-3 py-1 text-xs" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>Hero</button>
        <button className="rounded-full border border-slate-300/30 px-3 py-1 text-xs" onClick={() => loadAll(1, search, sort, "")}>World</button>
        <button className="rounded-full border border-slate-300/30 px-3 py-1 text-xs" onClick={() => setVoiceActive((v) => !v)}>Voice</button>
      </nav>

      {message && (
        <div className="fixed bottom-6 left-6 z-30 rounded-xl border border-cyan-300/35 bg-cyan-400/12 px-4 py-2 text-sm">
          {message}
        </div>
      )}

      {loading && <div className="fixed right-6 top-24 z-30 rounded-xl border border-fuchsia-300/30 bg-slate-950/90 px-3 py-2 text-sm">Syncing world...</div>}
    </div>
  );
}

export default App;
