import { useEffect, useState } from "react";
import "./App.css";

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

function App() {
  const [user, setUser] = useState(null);
  const [products, setProducts] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, per_page: 12, pages: 1, total: 0 });
  const [cart, setCart] = useState({ items: [], total: 0 });
  const [orders, setOrders] = useState([]);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("newest");
  const [authForm, setAuthForm] = useState({ username: "", email: "", password: "" });
  const [address, setAddress] = useState("");
  const [message, setMessage] = useState("");

  const loadAll = async (page = 1, query = search, sortBy = sort) => {
    const productUrl = `/api/products?page=${page}&per_page=12&sort=${encodeURIComponent(sortBy)}&search=${encodeURIComponent(query)}`;
    const [{ products: productList, pagination: pg }, me] = await Promise.all([api(productUrl), api("/api/auth/me")]);
    setProducts(productList || []);
    setPagination(pg || { page: 1, per_page: 12, pages: 1, total: 0 });
    if (me.authenticated) {
      setUser(me.user);
      const [cartData, ordersData] = await Promise.all([api("/api/cart"), api("/api/orders")]);
      setCart(cartData);
      setOrders(ordersData.orders || []);
    } else {
      setUser(null);
      setCart({ items: [], total: 0 });
      setOrders([]);
    }
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
    await api("/api/checkout", { method: "POST", body: JSON.stringify({ shipping_address: address }) });
    setAddress("");
    setMessage("Order placed successfully.");
    await loadAll();
  };

  return (
    <div className="page">
      <header className="topbar">
        <div>
          <h1>Ultimate AI Commerce</h1>
          <p className="subtitle">Production-style React storefront on your Flask backend</p>
        </div>
        <div className="auth-state">
          {user ? (
            <>
              <span>Hi, {user.username}</span>
              <button onClick={handleLogout}>Logout</button>
            </>
          ) : (
            <span>Guest</span>
          )}
        </div>
      </header>

      {message && <p className="message">{message}</p>}

      {!user && (
        <section className="card auth-grid">
          <form onSubmit={handleRegister}>
            <h2>Create Account</h2>
            <input placeholder="Username" value={authForm.username} onChange={(e) => setAuthForm({ ...authForm, username: e.target.value })} required />
            <input placeholder="Email" type="email" value={authForm.email} onChange={(e) => setAuthForm({ ...authForm, email: e.target.value })} required />
            <input placeholder="Password" type="password" value={authForm.password} onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })} required minLength={6} />
            <button type="submit">Register</button>
          </form>
          <form onSubmit={handleLogin}>
            <h2>Login</h2>
            <input placeholder="Username" value={authForm.username} onChange={(e) => setAuthForm({ ...authForm, username: e.target.value })} required />
            <input placeholder="Password" type="password" value={authForm.password} onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })} required />
            <button type="submit">Login</button>
          </form>
        </section>
      )}

      <section className="card">
        <div className="row">
          <h2>Products</h2>
          <div className="toolbar">
            <input placeholder="Search products..." value={search} onChange={(e) => setSearch(e.target.value)} />
            <select value={sort} onChange={(e) => setSort(e.target.value)}>
              <option value="newest">Newest</option>
              <option value="price_asc">Price: Low to High</option>
              <option value="price_desc">Price: High to Low</option>
            </select>
            <button onClick={() => loadAll(1, search, sort)}>Apply</button>
          </div>
        </div>
        <div className="grid">
          {products.map((product) => (
            <article className="product" key={product.id}>
              <h3>{product.name}</h3>
              <p>{product.description || "No description provided."}</p>
              <strong>${product.price.toFixed(2)}</strong>
              <button disabled={!user} onClick={() => addToCart(product.id)}>Add to cart</button>
            </article>
          ))}
        </div>
        <div className="pager">
          <button disabled={pagination.page <= 1} onClick={() => loadAll(pagination.page - 1, search, sort)}>
            Prev
          </button>
          <span>
            Page {pagination.page} of {Math.max(1, pagination.pages)}
          </span>
          <button
            disabled={pagination.page >= Math.max(1, pagination.pages)}
            onClick={() => loadAll(pagination.page + 1, search, sort)}
          >
            Next
          </button>
        </div>
      </section>

      <section className="card">
        <h2>Cart</h2>
        {cart.items.length === 0 ? (
          <p>No items yet.</p>
        ) : (
          <>
            {cart.items.map((item) => (
              <div className="cart-row" key={item.id}>
                <span>{item.product.name}</span>
                <input type="number" min="1" value={item.quantity} onChange={(e) => updateQty(item.id, Number(e.target.value))} />
                <span>${item.line_total.toFixed(2)}</span>
              </div>
            ))}
            <p className="total">Total: ${cart.total.toFixed(2)}</p>
          </>
        )}
        <form onSubmit={checkout} className="checkout">
          <input
            placeholder="Shipping address"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            required
            disabled={!user || cart.items.length === 0}
          />
          <button type="submit" disabled={!user || cart.items.length === 0}>Checkout</button>
        </form>
      </section>

      <section className="card">
        <h2>Order History</h2>
        {orders.length === 0 ? (
          <p>No orders yet.</p>
        ) : (
          orders.map((order) => (
            <div className="order" key={order.id}>
              <span>Order #{order.id}</span>
              <span>{order.status}</span>
              <span>${order.total_amount.toFixed(2)}</span>
            </div>
          ))
        )}
      </section>
    </div>
  );
}

export default App;
