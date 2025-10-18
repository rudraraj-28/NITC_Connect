// app.js - frontend logic (vanilla)
const API = 'http://127.0.0.1:5000/api';

const el = id => document.getElementById(id);
const qs = s => document.querySelector(s);

let authMode = 'login'; // or register

// Elements
const authForm = el('authForm');
const authTitle = el('authTitle');
const nameInput = el('name');
const emailInput = el('email');
const passInput = el('password');
const authMsg = el('authMsg');
const toggleAuth = el('toggleAuth');
const authSubmit = el('authSubmit');

const dashboard = el('dashboard');
const authCard = el('auth');
const userInfo = el('userInfo');
const viewArea = el('viewArea');
const logoutBtn = el('logout');

function setToken(token, name, role){
  localStorage.setItem('nc_token', token);
  localStorage.setItem('nc_name', name);
  localStorage.setItem('nc_role', role);
}

function getToken(){
  return localStorage.getItem('nc_token');
}
function getName(){ return localStorage.getItem('nc_name') || '' }
function getRole(){ return localStorage.getItem('nc_role') || 'student' }

function showDashboard(){
  authCard.classList.add('hidden');
  dashboard.classList.remove('hidden');
  userInfo.textContent = `${getName()} • ${getRole()}`;
  loadView('marketplace');
}

function showAuth(){
  authCard.classList.remove('hidden');
  dashboard.classList.add('hidden');
  authTitle.textContent = authMode === 'login' ? 'Login' : 'Register';
  nameInput.style.display = authMode === 'login' ? 'none' : 'block';
  toggleAuth.textContent = authMode === 'login' ? 'Switch to Register' : 'Switch to Login';
}

toggleAuth.addEventListener('click', ()=>{
  authMode = authMode === 'login' ? 'register' : 'login';
  showAuth();
});

authForm.addEventListener('submit', async (e)=>{
  e.preventDefault(); authMsg.textContent = '';
  const name = nameInput.value.trim();
  const email = emailInput.value.trim();
  const password = passInput.value;
  try{
    if(authMode === 'login'){
      const res = await fetch(API + '/auth/login', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({email, password})
      });
      const data = await res.json();
      if(data.error) { authMsg.textContent = data.error; return; }
      setToken(data.token, data.name, data.role);
      showDashboard();
    } else {
      const res = await fetch(API + '/auth/register', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({name, email, password})
      });
      const data = await res.json();
      if(data.error) { authMsg.textContent = data.error; return; }
      // server returns token
      setToken(data.token, name, 'student');
      showDashboard();
    }
  }catch(err){
    authMsg.textContent = 'Network error';
  }
});

// nav buttons
document.querySelectorAll('.navbtn').forEach(b=>{
  b.addEventListener('click', ()=> {
    loadView(b.dataset.view);
  });
});

logoutBtn.addEventListener('click', ()=>{
  localStorage.clear();
  window.location.reload();
});

// load initial state
if(getToken()){
  showDashboard();
} else {
  showAuth();
}

// VIEW RENDERERS
async function loadView(view){
  viewArea.innerHTML = '<h3>Loading...</h3>';
  const token = getToken();
  const headers = { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token };

  if(view === 'marketplace'){
    const res = await fetch(API + '/marketplace', { headers });
    const list = await res.json();
    renderMarketplace(list);
  } else if(view === 'lostfound'){
    const res = await fetch(API + '/lostfound', { headers });
    const list = await res.json();
    renderLostFound(list);
  } else if(view === 'events'){
    const res = await fetch(API + '/events', { headers });
    const list = await res.json();
    renderEvents(list);
  } else if(view === 'tickets'){
    const res = await fetch(API + '/tickets', { headers });
    const list = await res.json();
    renderTickets(list);
  } else if(view === 'bookings'){
    const res = await fetch(API + '/bookings', { headers });
    const list = await res.json();
    renderBookings(list);
  } else if(view === 'clubs'){
    const res = await fetch(API + '/clubs', { headers });
    const list = await res.json();
    renderClubs(list);
  } else if(view === 'placements'){
    const res = await fetch(API + '/placements', { headers });
    const list = await res.json();
    renderPlacements(list);
  } else {
    viewArea.innerHTML = '<div>Unknown view</div>';
  }
}

/* --- RENDER HELPERS --- */

function renderMarketplace(list){
  viewArea.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center">
      <h3>Marketplace</h3>
      <button id="newItemBtn" class="btn">New</button>
    </div>
    <div class="grid" id="marketGrid"></div>
  `;
  const grid = el('marketGrid');
  list.forEach(it=>{
    const div = document.createElement('div'); div.className = 'item';
    div.innerHTML = `<strong>${escapeHtml(it.title)}</strong>
      <div class="kv">by ${escapeHtml(it.owner||'you')} • ${it.created_at||''}</div>
      <p>${escapeHtml(it.description || '')}</p>
      <div class="kv">Price: ${escapeHtml(it.price || 'NA')}</div>
      <div style="margin-top:8px">
        ${ (it.owner === getName() || getRole()==='admin') ? `<button class="btn small" data-id="${it.id}" onclick="editMarket(${it.id})">Edit</button> <button class="btn alt small" onclick="deleteMarket(${it.id})">Delete</button>` : ''}
      </div>`;
    grid.appendChild(div);
  });
  el('newItemBtn').addEventListener('click', ()=> {
    showMarketForm();
  });
}

function showMarketForm(item = null){
  viewArea.innerHTML = `
    <h3>${item? 'Edit' : 'New'} Marketplace Item</h3>
    <input id="m_title" class="input" placeholder="Title" value="${item?escapeHtml(item.title):''}" />
    <textarea id="m_desc" class="input" placeholder="Description">${item?escapeHtml(item.description):''}</textarea>
    <input id="m_price" class="input" placeholder="Price" value="${item?escapeHtml(item.price):''}" />
    <div style="margin-top:8px"><button id="m_save" class="btn">Save</button> <button id="m_cancel" class="btn alt">Cancel</button></div>
    <div id="m_msg" class="msg"></div>
  `;
  el('m_cancel').addEventListener('click', ()=> loadView('marketplace'));
  el('m_save').addEventListener('click', async ()=>{
    const title = el('m_title').value.trim();
    const description = el('m_desc').value.trim();
    const price = el('m_price').value.trim();
    const token = getToken();
    try{
      let res;
      if(item){
        res = await fetch(API + '/marketplace', { method:'PUT', headers: {'Content-Type':'application/json','Authorization':'Bearer '+token}, body: JSON.stringify({ id: item.id, title, description, price })});
      } else {
        res = await fetch(API + '/marketplace', { method:'POST', headers: {'Content-Type':'application/json','Authorization':'Bearer '+token}, body: JSON.stringify({ title, description, price })});
      }
      const data = await res.json();
      if(data.error) el('m_msg').textContent = data.error;
      else loadView('marketplace');
    }catch(e){ el('m_msg').textContent='Network error' }
  });
}

window.editMarket = async function(id){
  const res = await fetch(API + '/marketplace', { headers: {'Authorization':'Bearer '+getToken()} });
  const list = await res.json();
  const item = list.find(x=>x.id===id);
  showMarketForm(item);
}

window.deleteMarket = async function(id){
  if(!confirm('Delete item?')) return;
  const res = await fetch(API + '/marketplace', { method:'DELETE', headers:{'Content-Type':'application/json','Authorization':'Bearer '+getToken()}, body: JSON.stringify({id})});
  const data = await res.json();
  if(data.error) alert(data.error); else loadView('marketplace');
}

/* LOST & FOUND */
function renderLostFound(list){
  viewArea.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center"><h3>Lost & Found</h3><button id="newLf" class="btn">Report</button></div><div class="grid" id="lfGrid"></div>`;
  const grid = el('lfGrid');
  list.forEach(it=>{
    const div = document.createElement('div'); div.className = 'item';
    div.innerHTML = `<strong>${escapeHtml(it.title)}</strong><div class="kv">by ${escapeHtml(it.owner||'you')} • ${escapeHtml(it.status)}</div><p>${escapeHtml(it.description)}</p>`;
    grid.appendChild(div);
  });
  el('newLf').addEventListener('click', ()=> showLfForm());
}

function showLfForm(){
  viewArea.innerHTML = `<h3>Report Lost/Found</h3><input id="lf_title" class="input" placeholder="Title"><textarea id="lf_desc" class="input" placeholder="Description"></textarea><select id="lf_status" class="input"><option value="lost">Lost</option><option value="found">Found</option></select><div style="margin-top:8px"><button id="lf_save" class="btn">Save</button><button id="lf_cancel" class="btn alt">Cancel</button></div><div id="lf_msg" class="msg"></div>`;
  el('lf_cancel').addEventListener('click', ()=> loadView('lostfound'));
  el('lf_save').addEventListener('click', async ()=>{
    const title = el('lf_title').value.trim(), description = el('lf_desc').value.trim(), status = el('lf_status').value;
    const res = await fetch(API + '/lostfound', { method:'POST', headers:{'Content-Type':'application/json','Authorization':'Bearer '+getToken()}, body: JSON.stringify({title,description,status})});
    const j = await res.json();
    if(j.error) el('lf_msg').textContent = j.error; else loadView('lostfound');
  });
}

/* EVENTS */
function renderEvents(list){
  viewArea.innerHTML = `<h3>Events</h3><div class="grid" id="evGrid"></div>`;
  const grid = el('evGrid');
  list.forEach(ev=>{
    const div = document.createElement('div'); div.className='item';
    div.innerHTML = `<strong>${escapeHtml(ev.title)}</strong><div class="kv">${escapeHtml(ev.start_date||'')} at ${escapeHtml(ev.venue||'')}</div><p>${escapeHtml(ev.description||'')}</p>`;
    grid.appendChild(div);
  });
}

/* TICKETS */
function renderTickets(list){
  viewArea.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center"><h3>Hostel Tickets</h3><button id="newTicket" class="btn">Raise Ticket</button></div><div id="tickGrid" class="grid"></div>`;
  const grid = el('tickGrid');
  list.forEach(t=>{
    const div = document.createElement('div'); div.className='item';
    div.innerHTML = `<strong>${escapeHtml(t.hostel || 'Hostel')}</strong><div class="kv">by ${escapeHtml(t.owner||'you')} • ${escapeHtml(t.status)}</div><p>${escapeHtml(t.issue)}</p>${ getRole()==='admin' ? `<div style="margin-top:8px"><button class="btn" onclick="updateTicket(${t.id},'closed')">Close</button></div>` : ''}`;
    grid.appendChild(div);
  });
  el('newTicket').addEventListener('click', ()=> showTicketForm());
}
function showTicketForm(){
  viewArea.innerHTML = `<h3>Raise Hostel Ticket</h3><input id="t_hostel" class="input" placeholder="Hostel"><textarea id="t_issue" class="input" placeholder="Describe the issue"></textarea><div style="margin-top:8px"><button id="t_save" class="btn">Submit</button><button id="t_cancel" class="btn alt">Cancel</button></div><div id="t_msg" class="msg"></div>`;
  el('t_cancel').addEventListener('click', ()=> loadView('tickets'));
  el('t_save').addEventListener('click', async ()=>{
    const hostel = el('t_hostel').value.trim(), issue = el('t_issue').value.trim();
    const res = await fetch(API + '/tickets', { method:'POST', headers:{'Content-Type':'application/json','Authorization':'Bearer '+getToken()}, body: JSON.stringify({hostel, issue})});
    const j = await res.json();
    if(j.error) el('t_msg').textContent = j.error; else loadView('tickets');
  });
}
window.updateTicket = async function(id, status){
  const res = await fetch(API + '/tickets', { method:'PUT', headers:{'Content-Type':'application/json','Authorization':'Bearer '+getToken()}, body: JSON.stringify({id, status})});
  const j = await res.json();
  if(j.error) alert(j.error); else loadView('tickets');
}

/* BOOKINGS */
function renderBookings(list){
  viewArea.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center"><h3>Hall Bookings</h3><button id="newBook" class="btn">Book Hall</button></div><div class="grid" id="bookGrid"></div>`;
  const g = el('bookGrid');
  list.forEach(b=>{
    const div = document.createElement('div'); div.className='item';
    div.innerHTML = `<strong>${escapeHtml(b.hall_name)}</strong><div class="kv">${escapeHtml(b.date)} • ${escapeHtml(b.slot)}</div><div class="kv">Status: ${escapeHtml(b.status)}</div>`;
    if(getRole()==='admin'){
      div.innerHTML += `<div style="margin-top:8px"><button class="btn" onclick="decideBooking(${b.id},'approved')">Approve</button> <button class="btn alt" onclick="decideBooking(${b.id},'rejected')">Reject</button></div>`;
    }
    g.appendChild(div);
  });
  el('newBook').addEventListener('click', showBookingForm);
}
function showBookingForm(){
  viewArea.innerHTML = `<h3>Book Hall</h3><input id="bk_hall" class="input" placeholder="Hall name"><input id="bk_date" class="input" placeholder="YYYY-MM-DD"><input id="bk_slot" class="input" placeholder="Slot (e.g. 10:00-12:00)"><div style="margin-top:8px"><button id="bk_save" class="btn">Submit</button><button id="bk_cancel" class="btn alt">Cancel</button></div><div id="bk_msg" class="msg"></div>`;
  el('bk_cancel').addEventListener('click', ()=> loadView('bookings'));
  el('bk_save').addEventListener('click', async ()=>{
    const hall_name = el('bk_hall').value.trim(), date = el('bk_date').value.trim(), slot = el('bk_slot').value.trim();
    const res = await fetch(API + '/bookings', { method:'POST', headers:{'Content-Type':'application/json','Authorization':'Bearer '+getToken()}, body: JSON.stringify({hall_name,date,slot})});
    const j = await res.json();
    if(j.error) el('bk_msg').textContent = j.error; else loadView('bookings');
  });
}
window.decideBooking = async function(id, status){
  const res = await fetch(API + '/bookings', { method:'PUT', headers:{'Content-Type':'application/json','Authorization':'Bearer '+getToken()}, body: JSON.stringify({id, status})});
  const j = await res.json();
  if(j.error) alert(j.error); else loadView('bookings');
}

/* CLUBS & PLACEMENTS */
function renderClubs(list){
  viewArea.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center"><h3>Clubs</h3>${ getRole()==='admin' ? '<button id="newClub" class="btn">New Club</button>': ''}</div><div class="grid" id="clubsGrid"></div>`;
  const g = el('clubsGrid');
  list.forEach(c=>{
    const div=document.createElement('div'); div.className='item';
    div.innerHTML = `<strong>${escapeHtml(c.name)}</strong><div class="kv">${escapeHtml(c.contact||'')}</div><p>${escapeHtml(c.description||'')}</p>`;
    g.appendChild(div);
  });
  if(getRole()==='admin') el('newClub').addEventListener('click', showClubForm);
}
function showClubForm(){
  viewArea.innerHTML = `<h3>New Club</h3><input id="cl_name" class="input" placeholder="Name"><input id="cl_contact" class="input" placeholder="Contact"><textarea id="cl_desc" class="input" placeholder="Description"></textarea><div style="margin-top:8px"><button id="cl_save" class="btn">Save</button><button id="cl_cancel" class="btn alt">Cancel</button></div><div id="cl_msg" class="msg"></div>`;
  el('cl_cancel').addEventListener('click', ()=> loadView('clubs'));
  el('cl_save').addEventListener('click', async ()=>{
    const name = el('cl_name').value.trim(), contact = el('cl_contact').value.trim(), description = el('cl_desc').value.trim();
    const res = await fetch(API + '/clubs', { method:'POST', headers:{'Content-Type':'application/json','Authorization':'Bearer '+getToken()}, body: JSON.stringify({name,contact,description})});
    const j = await res.json();
    if(j.error) el('cl_msg').textContent = j.error; else loadView('clubs');
  });
}

function renderPlacements(list){
  viewArea.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center"><h3>Placement Analytics</h3>${getRole()==='admin' ? '<button id="newPlace" class="btn">Add</button>' : ''}</div><div id="placeGrid" class="grid"></div>`;
  const g = el('placeGrid');
  list.forEach(p=>{
    const div=document.createElement('div'); div.className='item';
    div.innerHTML = `<strong>${escapeHtml(String(p.year))}</strong><div class="kv">Placed: ${escapeHtml(String(p.placed||'0'))}/${escapeHtml(String(p.total_students||'0'))}</div><div class="kv">Avg CTC: ${escapeHtml(String(p.avg_ctc||'0'))}</div>`;
    g.appendChild(div);
  });
  if(getRole()==='admin') el('newPlace').addEventListener('click', showPlaceForm);
}
function showPlaceForm(){
  viewArea.innerHTML = `<h3>Add Placement Data</h3><input id="pl_year" class="input" placeholder="Year"><input id="pl_total" class="input" placeholder="Total students"><input id="pl_placed" class="input" placeholder="Placed"><input id="pl_avg" class="input" placeholder="Avg CTC"><div style="margin-top:8px"><button id="pl_save" class="btn">Save</button><button id="pl_cancel" class="btn alt">Cancel</button></div><div id="pl_msg" class="msg"></div>`;
  el('pl_cancel').addEventListener('click', ()=> loadView('placements'));
  el('pl_save').addEventListener('click', async ()=>{
    const year = Number(el('pl_year').value.trim()), total = Number(el('pl_total').value.trim()), placed = Number(el('pl_placed').value.trim()), avg = Number(el('pl_avg').value.trim());
    const res = await fetch(API + '/placements', { method:'POST', headers:{'Content-Type':'application/json','Authorization':'Bearer '+getToken()}, body: JSON.stringify({year, total_students: total, placed, avg_ctc: avg})});
    const j = await res.json();
    if(j.error) el('pl_msg').textContent = j.error; else loadView('placements');
  });
}

/* UTIL */
function escapeHtml(s=""){ return String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;') }
function el(id){ return document.getElementById(id) }
