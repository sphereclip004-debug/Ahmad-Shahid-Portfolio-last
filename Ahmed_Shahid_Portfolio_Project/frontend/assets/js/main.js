(() => {
  'use strict';
  const $ = (selector, parent = document) => parent.querySelector(selector);
  const $$ = (selector, parent = document) => [...parent.querySelectorAll(selector)];
  const state = { data: null, skillCategory: 'all', projectCategory: 'all', skillSearch: '' };
  let toastTimer;

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }
  function showToast(message) {
    const toast = $('#toast');
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), 2800);
  }
  async function api(path, options = {}) {
    const response = await fetch(path, { credentials: 'same-origin', ...options, headers: { ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }), ...(options.headers || {}) } });
    let body = {};
    try { body = await response.json(); } catch (_) { /* non-JSON error */ }
    if (!response.ok) throw new Error(body.detail || body.message || `Request failed (${response.status})`);
    return body;
  }
  function textOr(value, fallback = '') { const result = String(value ?? '').trim(); return result || fallback; }
  function clear(node) { node.replaceChildren(); }
  function emptyState(container, message) { clear(container); container.append(el('div', 'empty-state', message)); }
  function setText(id, value, fallback) { const node = $('#' + id); if (node) node.textContent = textOr(value, fallback); }
  function safeLink(url) {
    try { const parsed = new URL(url, window.location.origin); return ['https:', 'http:'].includes(parsed.protocol) ? parsed.href : ''; }
    catch (_) { return ''; }
  }

  function renderSettings(settings) {
    const name = textOr(settings.portfolio_name, 'Ahmed Shahid');
    document.title = textOr(settings.browser_title, `${name} — Portfolio`);
    const meta = $('meta[name="description"]');
    if (meta) meta.content = textOr(settings.meta_description, 'Portfolio, education, skills, projects, and contact information.');
    setText('brand-name', name, 'Ahmed Shahid');
    setText('hero-intro', textOr(settings.intro, `Hello, I'm ${name}.`), `Hello, I'm ${name}.`);
    setText('hero-tagline', settings.tagline, 'Building thoughtful digital experiences');
    setText('hero-description', settings.hero_description, 'A place to share a professional journey, ideas, and work. Explore the sections below, or get in touch.');
    setText('about-text', settings.about_text, 'This portfolio is ready for verified biography details, skills, and project work. Use the Admin dashboard to personalize this section.');
    setText('about-name', name, 'Ahmed Shahid');
    setText('footer-name', name, 'Ahmed Shahid');
    setText('copyright-name', name, 'Ahmed Shahid');
    setText('footer-copy', settings.footer_text, `Designed with care · ${name}`);
    setText('hero-location', settings.location, 'Open to meaningful connections');
    $('#profile-image').alt = `Professional profile portrait of ${name}`;
    $('#profile-image').src = `/api/public/profile-image?v=${Date.now()}`;
    const px = Number(settings.profile_image_x); const py = Number(settings.profile_image_y);
    $('#profile-image').style.objectPosition = `${Number.isFinite(px) && settings.profile_image_x !== undefined ? px : 50}% ${Number.isFinite(py) && settings.profile_image_y !== undefined ? py : 27}%`;
    renderContactDetails(settings);
  }

  function renderContactDetails(settings) {
    const wrap = $('#contact-details');
    clear(wrap);
    let n = 0;
    const addDetail = (icon, label, value, href) => {
      const row = el('a', 'contact-detail');
      row.href = href;
      if (href.startsWith('http')) { row.target = '_blank'; row.rel = 'noopener noreferrer'; }
      const glyph = el('span', 'contact-detail-icon', icon);
      const detail = el('span');
      detail.append(el('strong', '', label), el('small', '', value));
      row.append(glyph, detail);
      wrap.append(row);
      n += 1;
    };
    const email = textOr(settings.contact_email);
    if (email) addDetail('@', 'Email', email, `mailto:${email}`);
    const whatsapp = textOr(settings.whatsapp_number);
    const digits = whatsapp.replace(/[^0-9]/g, '');
    if (digits.length >= 7) addDetail('↗', 'WhatsApp', whatsapp, `https://wa.me/${digits}`);
    const location = textOr(settings.location);
    if (location) {
      const row = el('div', 'contact-detail');
      row.append(el('span', 'contact-detail-icon', '⌖'));
      const detail = el('span'); detail.append(el('strong', '', 'Location'), el('small', '', location)); row.append(detail); wrap.append(row); n += 1;
    }
    if (!n) wrap.append(el('p', 'subtle-text', 'Contact details can be added from the Admin dashboard.'));
  }

  function renderEducation(items) {
    const wrap = $('#education-list'); clear(wrap);
    if (!items.length) return emptyState(wrap, 'Education entries will appear here after they are added in the Admin dashboard.');
    items.forEach((item, index) => {
      const data = item.data || {};
      const row = el('article', 'timeline-item reveal');
      const icon = el('div', 'timeline-icon', '⌂');
      const main = el('div');
      main.append(el('h3', '', textOr(data.institution, data.title || 'Education')));
      const qualification = textOr(data.qualification);
      if (qualification && !qualification.toLowerCase().startsWith('add verified')) main.append(el('p', 'qualification', qualification));
      const description = textOr(data.description);
      if (description && !description.toLowerCase().startsWith('education details can be completed')) main.append(el('p', '', description));
      const date = el('span', 'timeline-date', textOr(data.dates, 'Education'));
      row.append(icon, main, date);
      wrap.append(row);
      observeReveal(row);
    });
  }

  function renderSkills(items) {
    state.skills = items;
    const filterContainer = $('#skill-filters');
    const categories = [...new Set(items.map(x => textOr((x.data || {}).category, 'Other')))].sort((a, b) => a.localeCompare(b));
    clear(filterContainer);
    const all = el('button', `filter-chip${state.skillCategory === 'all' ? ' active' : ''}`, 'All skills');
    all.type = 'button'; all.dataset.category = 'all'; filterContainer.append(all);
    categories.forEach(category => {
      const button = el('button', `filter-chip${state.skillCategory === category ? ' active' : ''}`, category);
      button.type = 'button'; button.dataset.category = category; filterContainer.append(button);
    });
    filterContainer.onclick = event => {
      const button = event.target.closest('button[data-category]');
      if (!button) return;
      state.skillCategory = button.dataset.category;
      renderSkills(state.skills || []);
    };
    const wrap = $('#skills-grid'); clear(wrap);
    const filtered = items.filter(item => {
      const data = item.data || {};
      const category = textOr(data.category, 'Other');
      const haystack = `${data.title || ''} ${data.description || ''} ${category}`.toLowerCase();
      return (state.skillCategory === 'all' || category === state.skillCategory) && haystack.includes(state.skillSearch);
    });
    if (!filtered.length) return emptyState(wrap, items.length ? 'No skills match this search.' : 'Skills will appear here once verified skills are added in the Admin dashboard.');
    filtered.forEach(item => {
      const data = item.data || {};
      const card = el('article', 'skill-card reveal');
      const symbol = textOr(data.category, 'S').trim().slice(0, 2).toUpperCase();
      card.append(el('span', 'skill-icon', symbol));
      const label = el('span'); label.append(el('strong', '', textOr(data.title, 'Skill')), el('small', '', textOr(data.level, textOr(data.category, ''))));
      card.append(label); wrap.append(card); observeReveal(card);
    });
    const ticker = $('#skills-ticker'); clear(ticker);
    const words = items.length ? items.map(x => textOr(x.data?.title)).filter(Boolean) : ['Curiosity', 'Problem solving', 'Continuous learning'];
    [...words, ...words].forEach((word, i) => { ticker.append(el('span', '', word)); if (i < words.length * 2 - 1) ticker.append(el('b', '', '✳')); });
  }

  function renderServices(items) {
    const wrap = $('#services-grid'); clear(wrap);
    if (!items.length) return emptyState(wrap, 'Services can be listed here once your offerings are added in the Admin dashboard.');
    items.forEach((item, index) => {
      const data = item.data || {};
      const card = el('article', 'service-card reveal');
      card.append(el('div', 'service-icon', textOr(data.icon, ['✳', '↗', '◈'][index % 3])), el('h3', '', textOr(data.title, 'Service')));
      if (data.description) card.append(el('p', '', data.description));
      const href = safeLink(data.link || '');
      if (href) { const link = el('a', 'service-link', 'Learn more ↗'); link.href = href; link.target = '_blank'; link.rel = 'noopener noreferrer'; card.append(link); }
      wrap.append(card); observeReveal(card);
    });
  }

  function renderProjects(items) {
    state.projects = items;
    const filter = $('#project-filters');
    const categories = [...new Set(items.map(x => textOr(x.data?.category, 'Other')))].sort((a, b) => a.localeCompare(b));
    clear(filter);
    const all = el('button', `filter-chip${state.projectCategory === 'all' ? ' active' : ''}`, 'All projects'); all.type = 'button'; all.dataset.category = 'all'; filter.append(all);
    categories.forEach(category => { const b = el('button', `filter-chip${state.projectCategory === category ? ' active' : ''}`, category); b.type = 'button'; b.dataset.category = category; filter.append(b); });
    filter.onclick = event => { const button = event.target.closest('button[data-category]'); if (!button) return; state.projectCategory = button.dataset.category; renderProjects(state.projects || []); };
    const wrap = $('#projects-grid'); clear(wrap);
    const shown = items.filter(item => state.projectCategory === 'all' || textOr(item.data?.category, 'Other') === state.projectCategory);
    $('#project-count').textContent = items.length ? `${shown.length} item${shown.length === 1 ? '' : 's'}` : '';
    if (!shown.length) return emptyState(wrap, items.length ? 'No projects are in this category yet.' : 'Projects will appear here when you add and publish them from the Admin dashboard.');
    shown.forEach((item, index) => {
      const data = item.data || {};
      const card = el('article', 'project-card reveal');
      const art = el('div', 'project-art');
      if (data.image_url && safeLink(data.image_url)) {
        const img = el('img'); img.src = safeLink(data.image_url); img.alt = `${textOr(data.title, 'Project')} preview`; img.loading = 'lazy'; img.referrerPolicy = 'no-referrer';
        img.onerror = () => { img.remove(); art.append(createArtWindow()); };
        art.append(img);
      } else art.append(createArtWindow());
      const body = el('div', 'project-body');
      const top = el('div', 'project-topline'); top.append(el('span', 'project-category', textOr(data.category, 'Project')), el('span', 'project-number', String(index + 1).padStart(2, '0')));
      body.append(top, el('h3', '', textOr(data.title, 'Project')));
      if (data.description) body.append(el('p', '', data.description));
      const tags = textOr(data.technologies).split(/[,;|]/).map(x => x.trim()).filter(Boolean).slice(0, 8);
      if (tags.length) { const row = el('div', 'tag-row'); tags.forEach(tag => row.append(el('span', 'tag', tag))); body.append(row); }
      const bottom = el('div', 'project-bottom');
      const href = safeLink(data.link || '');
      if (href) { const a = el('a', 'project-link', 'View project ↗'); a.href = href; a.target = '_blank'; a.rel = 'noopener noreferrer'; bottom.append(a); }
      if (!href) bottom.append(el('span', 'subtle-text', 'Selected work'));
      body.append(bottom); card.append(art, body); wrap.append(card); observeReveal(card);
    });
  }

  function createArtWindow() {
    const windowBox = el('div', 'art-window'); const bar = el('div', 'art-window-bar');
    for (let i = 0; i < 3; i += 1) bar.append(el('i'));
    windowBox.append(bar, el('div', 'art-line accent'), el('div', 'art-line'), el('div', 'art-line short'), el('div', 'art-line'));
    return windowBox;
  }

  function renderReviews(items) {
    const wrap = $('#reviews-grid'); clear(wrap);
    if (!items.length) return emptyState(wrap, 'No public reviews yet. Approved reviews will appear here.');
    items.forEach(item => {
      const data = item.data || {};
      const card = el('article', 'review-card reveal');
      const rating = Math.max(1, Math.min(5, Number(data.rating) || 5));
      card.append(el('div', 'review-stars', '★'.repeat(rating) + '☆'.repeat(5 - rating)));
      card.append(el('blockquote', '', `“${textOr(data.message, '')}”`));
      const author = el('div', 'review-author');
      const initials = textOr(data.name, 'Guest').split(/\s+/).slice(0, 2).map(x => x[0]).join('').toUpperCase();
      author.append(el('span', 'avatar-initial', initials));
      const name = el('span'); name.append(el('strong', '', textOr(data.name, 'Guest')), el('small', '', textOr(data.role, 'Review'))); author.append(name);
      card.append(author); wrap.append(card); observeReveal(card);
    });
  }

  function observeReveal(node = document) {
    const nodes = node.matches?.('.reveal') ? [node] : $$('.reveal', node);
    nodes.forEach(item => {
      if (item.dataset.revealObserved) return;
      item.dataset.revealObserved = '1';
      if (!('IntersectionObserver' in window)) { item.classList.add('is-visible'); return; }
      revealObserver.observe(item);
    });
  }
  const revealObserver = 'IntersectionObserver' in window ? new IntersectionObserver(entries => entries.forEach(entry => {
    if (entry.isIntersecting) { entry.target.classList.add('is-visible'); revealObserver.unobserve(entry.target); }
  }), { threshold: .08, rootMargin: '0px 0px -15px 0px' }) : null;

  async function submitForm(form, endpoint, messageEl) {
    const button = $('button[type="submit"]', form);
    const original = button.innerHTML;
    button.disabled = true; button.textContent = 'Sending…'; messageEl.classList.remove('error'); messageEl.textContent = '';
    const formData = new FormData(form); const payload = Object.fromEntries(formData.entries());
    if (payload.rating) payload.rating = Number(payload.rating);
    try {
      const result = await api(endpoint, { method: 'POST', body: JSON.stringify(payload) });
      messageEl.textContent = result.message || 'Submitted successfully.';
      form.reset(); showToast(result.message || 'Submitted successfully.');
    } catch (error) {
      messageEl.textContent = error.message || 'Something went wrong. Please try again.'; messageEl.classList.add('error');
    } finally { button.disabled = false; button.innerHTML = original; }
  }

  function setupInteraction() {
    const toggle = $('#theme-toggle');
    let theme = 'dark';
    try { theme = localStorage.getItem('portfolio-theme') || 'dark'; } catch (_) { /* storage may be disabled */ }
    if (!['dark', 'light'].includes(theme)) theme = 'dark';
    document.body.dataset.theme = theme;
    const updateThemeTitle = () => { const light = document.body.dataset.theme === 'light'; toggle.title = light ? 'Switch to dark theme' : 'Switch to light theme'; toggle.setAttribute('aria-label', toggle.title); toggle.firstElementChild.textContent = light ? '☾' : '☼'; };
    updateThemeTitle();
    toggle.addEventListener('click', () => {
      document.body.dataset.theme = document.body.dataset.theme === 'dark' ? 'light' : 'dark';
      try { localStorage.setItem('portfolio-theme', document.body.dataset.theme); } catch (_) { /* storage may be disabled */ }
      updateThemeTitle();
    });
    const menuToggle = $('#menu-toggle'); const nav = $('#primary-nav');
    menuToggle.addEventListener('click', () => {
      const open = nav.classList.toggle('open'); menuToggle.setAttribute('aria-expanded', String(open)); menuToggle.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
    });
    $$('#primary-nav a').forEach(a => a.addEventListener('click', () => { nav.classList.remove('open'); menuToggle.setAttribute('aria-expanded', 'false'); }));
    const header = $('#site-header'); const backTop = $('#back-top-floating');
    const onScroll = () => { header.classList.toggle('scrolled', window.scrollY > 12); backTop.classList.toggle('visible', window.scrollY > 420); };
    window.addEventListener('scroll', onScroll, { passive: true }); onScroll();
    backTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
    $('#copy-email').addEventListener('click', async () => {
      const email = textOr(state.data?.settings?.contact_email);
      if (!email) return showToast('Email address is not configured yet.');
      try { await navigator.clipboard.writeText(email); showToast('Email address copied.'); }
      catch (_) { window.location.href = `mailto:${email}`; }
    });
    const chatFab = $('#chat-fab'); const chatPanel = $('#chat-panel');
    chatFab.addEventListener('click', () => { const open = chatPanel.hidden; chatPanel.hidden = !open; chatFab.setAttribute('aria-expanded', String(open)); });
    $('#chat-close').addEventListener('click', () => { chatPanel.hidden = true; chatFab.setAttribute('aria-expanded', 'false'); });
    $('#chat-contact-link').addEventListener('click', () => { chatPanel.hidden = true; chatFab.setAttribute('aria-expanded', 'false'); });
    $('#skill-search').addEventListener('input', event => { state.skillSearch = event.target.value.trim().toLowerCase(); renderSkills(state.skills || []); });
    $('#contact-form').addEventListener('submit', event => { event.preventDefault(); submitForm(event.currentTarget, '/api/public/contact', $('#contact-message')); });
    $('#review-form').addEventListener('submit', event => { event.preventDefault(); submitForm(event.currentTarget, '/api/public/reviews', $('#review-message')); });
    observeReveal(document);
  }

  async function loadPublicData() {
    try {
      const data = await api('/api/public/data');
      state.data = data;
      renderSettings(data.settings || {});
      renderEducation(data.education || []);
      renderSkills(data.skills || []);
      renderServices(data.services || []);
      renderProjects(data.projects || []);
      renderReviews(data.reviews || []);
    } catch (error) {
      showToast('Portfolio content could not be loaded. Check that the server is running.');
      emptyState($('#education-list'), 'Content could not be loaded. Please refresh the page.');
      emptyState($('#skills-grid'), 'Content could not be loaded. Please refresh the page.');
      emptyState($('#services-grid'), 'Content could not be loaded. Please refresh the page.');
      emptyState($('#projects-grid'), 'Content could not be loaded. Please refresh the page.');
      emptyState($('#reviews-grid'), 'Content could not be loaded. Please refresh the page.');
      console.error('Portfolio API unavailable:', error.message);
    } finally {
      $('#footer-year').textContent = String(new Date().getFullYear());
      observeReveal(document);
    }
  }

  setupInteraction();
  loadPublicData();
})();
