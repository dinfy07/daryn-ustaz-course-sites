const form = document.querySelector('#review-form');
const list = document.querySelector('#reviews');
const statusBox = document.querySelector('#status');
const fakeReviews = window.SITE_CONFIG.reviews;

function stars(value) {
  return `<span class="stars" aria-label="${value} из 5">${'★'.repeat(value)}${'☆'.repeat(5 - value)}</span>`;
}

function escapeHtml(value) {
  const node = document.createElement('div');
  node.textContent = value;
  return node.innerHTML;
}

function reviewCard(review) {
  const date = review.created_at ? new Date(review.created_at).toLocaleDateString(window.SITE_CONFIG.locale) : review.date;
  return `<article class="review"><div class="review-head"><strong>${escapeHtml(review.name)}</strong><time>${date}</time></div><p>${escapeHtml(review.comment)}</p>${stars(Number(review.stars))}</article>`;
}

async function loadReviews() {
  let submitted = [];
  try {
    const response = await fetch(`${window.SITE_CONFIG.api}/api/reviews/${window.SITE_CONFIG.slug}`);
    if (response.ok) submitted = await response.json();
  } catch (_) {
    statusBox.textContent = window.SITE_CONFIG.copy.offline;
  }
  list.innerHTML = [...submitted, ...fakeReviews].map(reviewCard).join('');
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const button = form.querySelector('button');
  const data = Object.fromEntries(new FormData(form));
  button.disabled = true;
  statusBox.textContent = window.SITE_CONFIG.copy.sending;
  try {
    const response = await fetch(`${window.SITE_CONFIG.api}/api/reviews/${window.SITE_CONFIG.slug}`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({...data, stars: Number(data.stars)}),
    });
    if (!response.ok) throw new Error('request failed');
    form.reset();
    form.querySelector('[name="stars"]').value = '5';
    statusBox.textContent = window.SITE_CONFIG.copy.success;
    await loadReviews();
  } catch (_) {
    statusBox.textContent = window.SITE_CONFIG.copy.error;
  } finally {
    button.disabled = false;
  }
});

loadReviews();
