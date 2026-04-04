'use strict';

// Injected by Django template
const URLS = {
  upload:  DJANGO_CTX.uploadUrl,
  ask:     DJANGO_CTX.askUrl,
  docInfo: DJANGO_CTX.docInfoUrl,
};

let currentDocId = DJANGO_CTX.docLoaded ? DJANGO_CTX.docId : null;

// ── Drag & Drop ────────────────────────────────────────────
const dropZone  = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');

dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault(); dropZone.classList.remove('drag-over');
  const f = e.dataTransfer.files[0];
  if (f) handleFile(f);
});
fileInput.addEventListener('change', () => { if (fileInput.files[0]) handleFile(fileInput.files[0]); });

// ── Upload ─────────────────────────────────────────────────
async function handleFile(file) {
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    alert('Please upload a PDF file.'); return;
  }

  showProgress(true);
  const fd = new FormData();
  fd.append('file', file);
  fd.append('csrfmiddlewaretoken', DJANGO_CTX.csrfToken);

  try {
    const res  = await fetch(URLS.upload, { method: 'POST', body: fd });
    const data = await res.json();
    showProgress(false);

    if (!res.ok || data.error) throw new Error(data.error || 'Upload failed');

    currentDocId = data.doc_id;
    showDocBadge(data.filename, data.num_words, data.num_chunks);
    enableQA();
    clearChat();
    addSystemMsg(`📄 <strong>${esc(data.filename)}</strong> loaded — ${(data.num_words || 0).toLocaleString()} words · ${data.num_chunks} chunks`);
  } catch (err) {
    showProgress(false);
    alert('Upload error: ' + err.message);
  }
}

function showProgress(visible) {
  document.getElementById('uploadProgress').hidden = !visible;
  dropZone.style.opacity   = visible ? '.4' : '1';
  dropZone.style.pointerEvents = visible ? 'none' : '';
}

function showDocBadge(filename, words, chunks) {
  const badge = document.getElementById('docBadge');
  document.getElementById('docName').textContent = filename;
  document.getElementById('docMeta').textContent =
    `${(words || 0).toLocaleString()} words · ${chunks || '—'} chunks`;
  badge.hidden = false;
}

function resetDocument() {
  currentDocId = null;
  document.getElementById('docBadge').hidden = true;
  fileInput.value = '';
  disableQA();
  clearChat();
  // Tell server to clear session
  fetch(URLS.upload, { method: 'POST',
    headers: { 'X-Reset': '1', 'X-CSRFToken': DJANGO_CTX.csrfToken } })
    .catch(() => {});
}

// ── QA enable / disable ─────────────────────────────────────
function enableQA() {
  const inp = document.getElementById('questionInput');
  const btn = document.getElementById('askBtn');
  inp.disabled = false;
  btn.disabled = false;
  inp.focus();
}
function disableQA() {
  document.getElementById('questionInput').disabled = true;
  document.getElementById('askBtn').disabled = true;
}

// ── Ask ─────────────────────────────────────────────────────
document.getElementById('questionInput').addEventListener('keydown', e => {
  if (e.key === 'Enter') askQuestion();
});

async function askQuestion() {
  const inp      = document.getElementById('questionInput');
  const question = inp.value.trim();
  if (!question) return;
  if (!currentDocId) { alert('Please upload a document first.'); return; }

  inp.value = '';
  addUserMsg(question);
  const typingEl = addTyping();

  try {
    const res  = await fetch(URLS.ask, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': DJANGO_CTX.csrfToken,
      },
      body: JSON.stringify({ question, doc_id: currentDocId }),
    });
    const data = await res.json();
    typingEl.remove();

    if (!res.ok || data.error) { addErrorMsg(data.error || 'Something went wrong.'); return; }
    addBotMsg(data);
  } catch (err) {
    typingEl.remove();
    addErrorMsg('Network error: ' + err.message);
  }
}

// ── Chat Helpers ────────────────────────────────────────────
function clearChat() {
  document.getElementById('chatWindow').innerHTML =
    `<div class="empty-state" id="emptyState">
       <div class="empty-icon">💬</div>
       <p>Ask anything about your document</p>
     </div>`;
}

function removeEmpty() {
  const e = document.getElementById('emptyState');
  if (e) e.remove();
}

function addSystemMsg(html) {
  removeEmpty();
  const cw = document.getElementById('chatWindow');
  const d  = document.createElement('div');
  d.className = 'sys-msg';
  d.innerHTML = html;
  cw.appendChild(d);
  cw.scrollTop = cw.scrollHeight;
}

function addUserMsg(text) {
  removeEmpty();
  const cw = document.getElementById('chatWindow');
  const d  = document.createElement('div');
  d.className = 'msg user';
  d.innerHTML = `<div class="bubble">${esc(text)}</div>`;
  cw.appendChild(d);
  cw.scrollTop = cw.scrollHeight;
}

function addTyping() {
  removeEmpty();
  const cw = document.getElementById('chatWindow');
  const d  = document.createElement('div');
  d.className = 'msg bot';
  d.innerHTML = `<div class="bubble"><div class="typing"><span></span><span></span><span></span></div></div>`;
  cw.appendChild(d);
  cw.scrollTop = cw.scrollHeight;
  return d;
}

function addBotMsg(data) {
  const cw      = document.getElementById('chatWindow');
  const d       = document.createElement('div');
  d.className   = 'msg bot';
  const conf    = Math.min(100, data.confidence || 0);
  const color   = conf > 60 ? 'var(--success)' : conf > 30 ? 'var(--accent)' : '#ff8080';

  const srcHtml = (data.sources || []).map(s =>
    `<div class="source-item">
       <div class="source-sim">similarity: ${s.similarity}</div>
       <div>${esc(s.text)}</div>
     </div>`
  ).join('');

  d.innerHTML = `
    <div class="bubble">
      <div class="answer-text">${esc(data.answer)}</div>
      <div class="confidence">
        <div class="conf-bar">
          <div class="conf-fill" style="width:${conf}%;background:${color}"></div>
        </div>
        <span>${conf}% confidence</span>
      </div>
      ${srcHtml ? `
        <button class="sources-toggle" onclick="toggleSrc(this)">▸ Show sources (${data.sources.length})</button>
        <div class="sources-list">${srcHtml}</div>` : ''}
    </div>`;
  cw.appendChild(d);
  cw.scrollTop = cw.scrollHeight;
}

function toggleSrc(btn) {
  const list = btn.nextElementSibling;
  const open = list.classList.toggle('open');
  btn.textContent = open
    ? btn.textContent.replace('▸ Show', '▾ Hide')
    : btn.textContent.replace('▾ Hide', '▸ Show');
}

function addErrorMsg(text) {
  const cw = document.getElementById('chatWindow');
  const d  = document.createElement('div');
  d.className = 'msg bot';
  d.innerHTML = `<div class="error-bubble">⚠ ${esc(text)}</div>`;
  cw.appendChild(d);
  cw.scrollTop = cw.scrollHeight;
}

function esc(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
