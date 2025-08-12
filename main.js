const genBtn = document.getElementById('genBtn');
const resultCard = document.getElementById('resultCard');
const skuText = document.getElementById('skuText');
const copyBtn = document.getElementById('copyBtn');
const errorBox = document.getElementById('error');

async function generateSKU() {
  errorBox.classList.add('hidden');
  try {
    const res = await fetch('/api/next', { method: 'POST' });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      const msg = data.error || `Error: ${res.status}`;
      throw new Error(msg);
    }
    const data = await res.json();
    skuText.textContent = data.sku;
    resultCard.classList.remove('hidden');
  } catch (err) {
    errorBox.textContent = err.message || 'An error occurred.';
    errorBox.classList.remove('hidden');
  }
}

genBtn.addEventListener('click', generateSKU);

copyBtn.addEventListener('click', async () => {
  const text = skuText.textContent.trim();
  if (!text || text === '----') return;
  try {
    await navigator.clipboard.writeText(text);
    copyBtn.textContent = 'Copied';
    setTimeout(() => (copyBtn.textContent = 'Copy'), 1200);
  } catch {
    // ignore
  }
});
