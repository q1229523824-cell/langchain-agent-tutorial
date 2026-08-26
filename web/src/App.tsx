import { FormEvent, useEffect, useMemo, useState } from "react";

const API = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

type Message = { role: "user" | "assistant"; content: string };
type Product = { sku: string; name: string; category: string; price: string; stock: number };
type Order = { order_id: string; status: string; amount: string; product_name: string };

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API}${path}`, { ...options, headers });
  const body = await response.json();
  if (!response.ok) throw new Error(body?.error?.message ?? body?.detail ?? "请求失败");
  return body as T;
}

async function streamChat(threadId: string, message: string, token: string, onDelta: (text: string) => void) {
  const response = await fetch(`${API}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ thread_id: threadId, message }),
  });
  if (!response.ok || !response.body) throw new Error("聊天流建立失败");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const chunk = await reader.read();
    if (chunk.done) break;
    buffer += decoder.decode(chunk.value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const event = JSON.parse(line.slice(6));
      if (event.content) onDelta(event.content);
    }
  }
}

export default function App() {
  const [token, setToken] = useState(localStorage.getItem("xinghe_token") ?? "");
  const [userId, setUserId] = useState("demo-user");
  const [password, setPassword] = useState("demo-password");
  const [threadId] = useState(() => `web-${crypto.randomUUID().slice(0, 8)}`);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [products, setProducts] = useState<Product[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const loggedIn = Boolean(token);

  const pendingOrder = useMemo(() => orders.find((order) => order.status === "待发货"), [orders]);

  async function login(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const result = await request<{ access_token: string }>("/auth/login", {
        method: "POST", body: JSON.stringify({ user_id: userId, password }),
      });
      localStorage.setItem("xinghe_token", result.access_token);
      setToken(result.access_token);
    } catch (exception) { setError(exception instanceof Error ? exception.message : "登录失败"); }
  }

  async function loadData() {
    if (!token) return;
    try {
      const [productResult, orderResult] = await Promise.all([
        request<{ products: Product[] }>("/products?in_stock_only=true", {}, token),
        request<{ orders: Order[] }>("/orders", {}, token),
      ]);
      setProducts(productResult.products);
      setOrders(orderResult.orders);
    } catch (exception) { setError(exception instanceof Error ? exception.message : "加载失败"); }
  }

  useEffect(() => { void loadData(); }, [token]);

  async function sendMessage(event: FormEvent) {
    event.preventDefault();
    const text = input.trim();
    if (!text || busy || !token) return;
    setInput(""); setError(""); setBusy(true);
    setMessages((current) => [...current, { role: "user", content: text }, { role: "assistant", content: "" }]);
    try {
      await streamChat(threadId, text, token, (delta) => setMessages((current) => {
        const next = [...current]; next[next.length - 1] = { role: "assistant", content: next[next.length - 1].content + delta }; return next;
      }));
    } catch (exception) { setError(exception instanceof Error ? exception.message : "聊天失败"); }
    finally { setBusy(false); void loadData(); }
  }

  async function previewRefund() {
    if (!pendingOrder || !token) return;
    setError("");
    try {
      const result = await request<{ confirmation_id: string; amount: string }>("/refunds/prepare", {
        method: "POST", body: JSON.stringify({ order_id: pendingOrder.order_id }),
      }, token);
      if (window.confirm(`确认退款 ${result.amount}？\n确认编号：${result.confirmation_id}`)) {
        await request(`/refunds/${result.confirmation_id}/confirm`, { method: "POST" }, token);
        await loadData();
        window.alert("已提交退款确认，请通过退款状态查询最终结果。");
      }
    } catch (exception) { setError(exception instanceof Error ? exception.message : "退款失败"); }
  }

  if (!loggedIn) return <main className="auth-shell"><form className="card auth-card" onSubmit={login}><p className="eyebrow">XINGHE COMMERCE AGENT</p><h1>星河商城</h1><p>Python Agent 编排 · Java 业务服务</p><label>用户 ID<input value={userId} onChange={(event) => setUserId(event.target.value)} /></label><label>密码<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label><button type="submit">登录演示系统</button>{error && <p className="error">{error}</p>}</form></main>;

  return <main className="shell"><header><div><p className="eyebrow">XINGHE COMMERCE AGENT</p><h1>星河商城客服 Agent</h1><p className="muted">Thread: {threadId} · 用户: {userId}</p></div><button className="ghost" onClick={() => { localStorage.removeItem("xinghe_token"); setToken(""); }}>退出</button></header><section className="grid"><div className="card chat-card"><div className="messages">{messages.length === 0 && <p className="empty">试试问：“order-1001 能不能退款？”或“推荐适合通勤的耳机”。</p>}{messages.map((message, index) => <div className={`message ${message.role}`} key={`${index}-${message.content.slice(0, 6)}`}><span>{message.role === "user" ? "你" : "Agent"}</span><p>{message.content || "正在生成…"}</p></div>)}</div><form className="composer" onSubmit={sendMessage}><input value={input} onChange={(event) => setInput(event.target.value)} placeholder="输入你的问题…" disabled={busy} /><button disabled={busy}>{busy ? "处理中" : "发送"}</button></form></div><aside className="side"><div className="card"><h2>商品</h2>{products.map((product) => <div className="row" key={product.sku}><span>{product.name}<small>{product.category}</small></span><strong>¥{product.price}</strong></div>)}</div><div className="card"><h2>订单</h2>{orders.map((order) => <div className="row" key={order.order_id}><span>{order.order_id}<small>{order.product_name}</small></span><strong>{order.status}</strong></div>)}{pendingOrder && <button onClick={previewRefund}>预览并确认退款</button>}</div></aside></section>{error && <div className="toast error">{error}</div>}</main>;
}
