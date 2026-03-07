import { useEffect, useMemo, useState } from 'react'

const DELIVERY_FEE = 5

function getApiUrl(path) {
  const base = window.APP_CONFIG?.API_BASE_URL || ''
  return `${base}${path}`
}

export default function App() {
  const [products, setProducts] = useState([])
  const [cart, setCart] = useState({})
  const [status, setStatus] = useState('')
  const [form, setForm] = useState({
    full_name: '',
    phone: '',
    street: '',
    city: '',
    zip: '',
    payment_method: ''
  })

  useEffect(() => {
    async function loadProducts() {
      try {
        const res = await fetch(getApiUrl('/api/products'))
        const data = await res.json()
        if (!res.ok || !Array.isArray(data.products)) throw new Error('Failed')
        setProducts(data.products)
      } catch {
        setStatus('Could not load products from API.')
      }
    }
    loadProducts()
  }, [])

  const subtotal = useMemo(() => {
    return Object.entries(cart).reduce((sum, [id, qty]) => {
      const product = products.find((p) => p.id === Number(id))
      if (!product) return sum
      return sum + product.price * qty
    }, 0)
  }, [cart, products])

  const itemCount = useMemo(() => {
    return Object.values(cart).reduce((sum, qty) => sum + qty, 0)
  }, [cart])

  const total = subtotal > 0 ? subtotal + DELIVERY_FEE : 0

  function addToCart(id) {
    setCart((prev) => ({ ...prev, [id]: (prev[id] || 0) + 1 }))
  }

  function updateQty(id, delta) {
    setCart((prev) => {
      const next = (prev[id] || 0) + delta
      const copy = { ...prev }
      if (next <= 0) delete copy[id]
      else copy[id] = next
      return copy
    })
  }

  async function submitCheckout(e) {
    e.preventDefault()
    setStatus('')

    if (Object.keys(cart).length === 0) {
      setStatus('Add at least one product before checkout.')
      return
    }

    if (!form.full_name || !form.phone || !form.street || !form.city || !form.zip || !form.payment_method) {
      setStatus('Please complete all address and payment fields.')
      return
    }

    const payload = {
      cart_items: Object.entries(cart).map(([id, qty]) => ({ id: Number(id), qty })),
      address: {
        full_name: form.full_name,
        phone: form.phone,
        street: form.street,
        city: form.city,
        zip: form.zip
      },
      payment_method: form.payment_method
    }

    try {
      const res = await fetch(getApiUrl('/api/checkout'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      const data = await res.json()
      if (!res.ok) {
        setStatus(data.detail || 'Checkout failed.')
        return
      }
      setStatus(`${data.message} Order ID: ${data.order.order_id}`)
      setCart({})
      setForm({ full_name: '', phone: '', street: '', city: '', zip: '', payment_method: '' })
    } catch {
      setStatus('Network error. Please try again.')
    }
  }

  return (
    <div className="page">
      <header className="topbar">
        <h1>Web Shop</h1>
        <p>Cart ({itemCount})</p>
      </header>

      <main className="layout">
        <section className="panel">
          <h2>Products</h2>
          <div className="grid">
            {products.map((product) => (
              <article key={product.id} className="card">
                <p className="title">{product.name}</p>
                <p>${product.price.toFixed(2)}</p>
                <button onClick={() => addToCart(product.id)}>Add to Cart</button>
              </article>
            ))}
          </div>
        </section>

        <aside className="panel">
          <h2>Your Cart</h2>
          <ul className="cart-list">
            {Object.keys(cart).length === 0 && <li>Your cart is empty.</li>}
            {Object.entries(cart).map(([id, qty]) => {
              const p = products.find((x) => x.id === Number(id))
              if (!p) return null
              return (
                <li key={id} className="cart-item">
                  <span>{p.name}</span>
                  <div className="actions">
                    <button onClick={() => updateQty(Number(id), -1)}>-</button>
                    <span>{qty}</span>
                    <button onClick={() => updateQty(Number(id), 1)}>+</button>
                  </div>
                </li>
              )
            })}
          </ul>

          <p>Subtotal: ${subtotal.toFixed(2)}</p>
          <p>Delivery: ${subtotal > 0 ? DELIVERY_FEE.toFixed(2) : '0.00'}</p>
          <p><strong>Total: ${total.toFixed(2)}</strong></p>

          <form className="checkout" onSubmit={submitCheckout}>
            <h3>Delivery Address</h3>
            <input placeholder="Full name" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
            <input placeholder="Phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            <input placeholder="Street" value={form.street} onChange={(e) => setForm({ ...form, street: e.target.value })} />
            <input placeholder="City" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
            <input placeholder="ZIP" value={form.zip} onChange={(e) => setForm({ ...form, zip: e.target.value })} />

            <h3>Payment</h3>
            <select value={form.payment_method} onChange={(e) => setForm({ ...form, payment_method: e.target.value })}>
              <option value="">Select payment method</option>
              <option value="card">Credit/Debit Card</option>
              <option value="cash">Cash on Delivery</option>
            </select>

            <button type="submit">Pay and Place Order</button>
          </form>
          <p className="status">{status}</p>
        </aside>
      </main>
    </div>
  )
}
