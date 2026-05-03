const API = window.VANT2_API_URL || 'https://vant2.onrender.com';
let token = '';
let activeChatId = '1';

const chatsEl = document.getElementById('chats');
const messagesEl = document.getElementById('messages');
const chatTitleEl = document.getElementById('chatTitle');

function authHeaders() {
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

document.getElementById('sendOtp').onclick = async () => {
  const phone = document.getElementById('phone').value;
  const res = await fetch(`${API}/v1/auth/send-otp`, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ phone })
  });
  if (!res.ok) return alert('Ошибка отправки OTP');
  alert('OTP отправлен (dev code: 123456)');
};

document.getElementById('verifyOtp').onclick = async () => {
  const phone = document.getElementById('phone').value;
  const code = document.getElementById('otp').value;
  const res = await fetch(`${API}/v1/auth/verify-otp`, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ phone, code })
  });
  if (!res.ok) return alert('Ошибка верификации OTP');
  const data = await res.json();
  token = data.token;
  await loadChats();
};

document.getElementById('sendMsg').onclick = async () => {
  const text = document.getElementById('msgInput').value.trim();
  if (!text) return;
  const res = await fetch(`${API}/v1/messages`, {
    method:'POST',
    headers:{'Content-Type':'application/json', ...authHeaders()},
    body: JSON.stringify({ chat_id: activeChatId, text, sender: 'web-user' })
  });
  if (!res.ok) return alert('Ошибка отправки сообщения');
  document.getElementById('msgInput').value = '';
  await loadMessages();
};

async function loadChats(){
  const res = await fetch(`${API}/v1/chats`, { headers: authHeaders() });
  if (!res.ok) return alert('Не удалось загрузить чаты');
  const chats = await res.json();
  chatsEl.innerHTML = '';
  chats.forEach(c => {
    const item = document.createElement('div');
    item.className = 'chat-item';
    item.textContent = c.title;
    item.onclick = () => { activeChatId = c.id; chatTitleEl.textContent = c.title; loadMessages(); };
    chatsEl.appendChild(item);
  });
}

async function loadMessages(){
  const res = await fetch(`${API}/v1/messages?chat_id=${activeChatId}`, { headers: authHeaders() });
  if (!res.ok) return alert('Не удалось загрузить сообщения');
  const msgs = await res.json();
  messagesEl.innerHTML = '';
  msgs.forEach(m => {
    const d = document.createElement('div');
    d.className = 'msg';
    d.textContent = m.text;
    messagesEl.appendChild(d);
  });
}
