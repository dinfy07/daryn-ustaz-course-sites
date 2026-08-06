const api = window.ADMIN_API;
const login = document.querySelector('#login');
const editor = document.querySelector('#editor');
const logout = document.querySelector('#logout');
const courses = document.querySelector('#courses');
const loginStatus = document.querySelector('#login-status');
const editorStatus = document.querySelector('#editor-status');
let password = sessionStorage.getItem('daryn_admin_password') || '';

function escapeHtml(value) {
  const node = document.createElement('div'); node.textContent = value; return node.innerHTML;
}

async function request(path, options = {}) {
  const response = await fetch(`${api}${path}`, {...options, headers: {...options.headers, Authorization: `Bearer ${password}`, 'Content-Type': 'application/json'}});
  if (response.status === 401) throw new Error('Неверный пароль');
  if (!response.ok) throw new Error('Не удалось выполнить запрос');
  return response.json();
}

function courseCard(site) {
  return `<form class="course" data-slug="${site.slug}"><div class="badge">${site.slug.replace('course-', 'Курс ')}</div><h3>${escapeHtml(site.title)}</h3><label>Ссылка кнопки «Ознакомиться с программой»<input type="url" name="program_url" value="${escapeHtml(site.program_url)}" required pattern="https://.*"></label><div class="actions"><button type="submit">Сохранить</button><a href="${escapeHtml(site.program_url)}" target="_blank" rel="noopener">Проверить ссылку</a><span role="status"></span></div></form>`;
}

async function loadCourses() {
  editorStatus.textContent = 'Загрузка...';
  try {
    const sites = await request('/api/admin/sites');
    courses.innerHTML = sites.map(courseCard).join('');
    login.hidden = true; editor.hidden = false; logout.hidden = false; editorStatus.textContent = '';
  } catch (error) {
    sessionStorage.removeItem('daryn_admin_password'); password = ''; login.hidden = false; editor.hidden = true; logout.hidden = true; loginStatus.textContent = error.message;
  }
}

document.querySelector('#login-form').addEventListener('submit', async (event) => {
  event.preventDefault(); password = new FormData(event.currentTarget).get('password'); loginStatus.textContent = 'Проверка...';
  sessionStorage.setItem('daryn_admin_password', password); await loadCourses();
});

courses.addEventListener('submit', async (event) => {
  const form = event.target.closest('.course'); if (!form) return; event.preventDefault();
  const status = form.querySelector('[role="status"]'); const button = form.querySelector('button'); const url = new FormData(form).get('program_url').trim();
  button.disabled = true; status.textContent = 'Сохраняем...';
  try { const site = await request(`/api/admin/sites/${form.dataset.slug}`, {method:'PATCH', body:JSON.stringify({program_url:url})}); form.querySelector('a').href = site.program_url; status.textContent = 'Сохранено'; }
  catch (error) { status.textContent = error.message; }
  finally { button.disabled = false; }
});

document.querySelector('#refresh').addEventListener('click', loadCourses);
logout.addEventListener('click', () => { sessionStorage.removeItem('daryn_admin_password'); password=''; login.hidden=false; editor.hidden=true; logout.hidden=true; loginStatus.textContent=''; });
if (password) loadCourses();
