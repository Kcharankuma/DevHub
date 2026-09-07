let catalog = [];
let categoryNames = {};
let activeFilter = 'all';
let searchQuery = '';

const contentArea = document.getElementById('contentArea');
const searchInput = document.getElementById('searchInput');
const pillButtons = document.querySelectorAll('.pill-btn');
const noResults = document.getElementById('noResults');

async function init() {
  try {
    const res = await fetch('/api/catalog');
    const data = await res.json();
    catalog = data.catalog;
    categoryNames = data.categories;
    renderCatalog();
  } catch (err) {
    console.error('Error fetching data from server:', err);
  }
}

function directDownload(url) {
  const a = document.createElement('a');
  a.href = url;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

function handleAction(actionKey) {
  directDownload(`/api/download/${actionKey}`);
}

function renderCatalog() {
  contentArea.innerHTML = '';

  const filtered = catalog.filter(item => {
    const matchesCategory = activeFilter === 'all' || item.category === activeFilter;
    const matchesSearch = item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.desc.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  if (filtered.length === 0) {
    noResults.style.display = 'block';
    return;
  }
  noResults.style.display = 'none';

  const grouped = {};
  filtered.forEach(item => {
    if (!grouped[item.category]) grouped[item.category] = [];
    grouped[item.category].push(item);
  });

  Object.keys(categoryNames).forEach(catKey => {
    if (grouped[catKey] && grouped[catKey].length > 0) {
      const section = document.createElement('div');
      section.className = 'category-section';

      section.innerHTML = `
        <h2 class="category-title">
          ${categoryNames[catKey]}
          <span class="count">${grouped[catKey].length}</span>
        </h2>
        <div class="grid" id="grid-${catKey}"></div>
      `;

      contentArea.appendChild(section);
      const grid = section.querySelector(`#grid-${catKey}`);

      grouped[catKey].forEach(item => {
        const card = document.createElement('div');
        card.className = 'card';

        const btnHtml = item.action
          ? `<button class="download-btn" onclick="handleAction('${item.action}')">⬇ Download Template</button>`
          : `<button class="download-btn" onclick="directDownload('${item.url}')">⬇ Download Installer</button>`;

        card.innerHTML = `
          <i class="${item.icon}"></i>
          <h3>${item.name}</h3>
          <span class="version-tag">${item.version}</span>
          <p>${item.desc}</p>
          ${btnHtml}
        `;
        grid.appendChild(card);
      });
    }
  });
}

searchInput.addEventListener('input', (e) => {
  searchQuery = e.target.value.trim();
  renderCatalog();
});

pillButtons.forEach(btn => {
  btn.addEventListener('click', () => {
    pillButtons.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeFilter = btn.getAttribute('data-filter');
    renderCatalog();
  });
});

init();