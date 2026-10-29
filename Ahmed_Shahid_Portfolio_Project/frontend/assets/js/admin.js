(() => {
  'use strict';
  const $ = (selector, parent = document) => parent.querySelector(selector);
  const state = { csrf: '', username: '', authenticated: false, tab: 'overview', editorKind: '', editorId: null, contentItems: [] };
  let toastTimer;
  const titles = { overview: 'Overview', settings: 'Site settings', education: 'Education', skills: 'Skills', services: 'Services', projects: 'Projects', reviews: 'Reviews', cv: 'CV & profile image', messages: 'Contact messages', audit: 'Audit log' };
  const kinds = {
    education: { label: 'education entry', plural: 'Education', fields: [
      ['institution', 'School / college / institution', 'text', true, true], ['qualification', 'Qualification', 'text', false, false], ['dates', 'Dates', 'text', false, false], ['description', 'Description', 'textarea', false, true]
    ]},
    skills: { label: 'skill', plural: 'Skills', fields: [
      ['title', 'Skill name', 'text', true, false], ['category', 'Category', 'text', false, false], ['level', 'Level / proficiency label', 'text', false, false], ['description', 'Short description', 'textarea', false, true]
    ]},
    services: { label: 'service', plural: 'Services', fields: [
      ['title', 'Service title', 'text', true, false], ['description', 'Description', 'textarea', true, true], ['icon', 'Small icon / symbol', 'text', false, false], ['link', 'External link (optional)', 'url', false, false]
    ]},
    projects: { label: 'project', plural: 'Projects', fields: [
      ['title', 'Project title', 'text', true, false], ['description', 'Description', 'textarea', true, true], ['category', 'Category', 'text', false, false], ['technologies', 'Technology labels (comma-separated)', 'text', false, true], ['link', 'Project link (optional)', 'url', false, false], ['image_url', 'Project image URL or uploaded image path', 'text', false, false]
    ]},
    reviews: { label: 'review', plural: 'Reviews', fields: [
      ['name', 'Reviewer name', 'text', true, false], ['role', 'Role / relationship', 'text', false, false], ['rating', 'Rating (1–5)', 'number', true, false], ['message', 'Review text', 'textarea', true, true]
    ]}
  };
  const settingsFields = [
    ['portfolio_name', 'Public portfolio name', 'text', false], ['cv_name', 'Name displayed on CV', 'text', false],
    ['browser_title', 'Browser title', 'text', false], ['meta_description', 'Search description', 'textarea', true],
    ['tagline', 'Hero headline', 'text', true], ['intro', 'Hero introduction', 'text', true], ['hero_description', 'Hero supporting text', 'textarea', true],
    ['about_text', 'About section text', 'textarea', true], ['footer_text', 'Footer text', 'text', true],
    ['contact_email', 'Public contact email', 'email', false], ['whatsapp_number', 'WhatsApp number (include country code)', 'text', false], ['location', 'Location label', 'text', false]
  ];
  const cvFields = [
    ['headline', 'Professional headline', 'text', false], ['summary', 'Professional summary', 'textarea', true],
    ['email', 'Email address', 'email', false], ['phone', 'Phone number', 'text', false], ['location', 'Location', 'text', false],
    ['work_experience', 'Work experience (one entry per line)', 'textarea', true], ['certifications', 'Certifications (one per line)', 'textarea', true],
    ['achievements', 'Achievements (one per line)', 'textarea', true], ['additional_information', 'Additional information', 'textarea', true]
  ];

  function node(tag, className, text) { const n = document.createElement(tag); if (className) n.className = className; if (text !== undefined && text !== null) n.textContent = String(text); return n; }
  function toast(message) { const el = $('#admin-toast'); el.textContent = message; el.classList.add('show'); clearTimeout(toastTimer); toastTimer = setTimeout(() => el.classList.remove('show'), 3000); }
  function notice(message, isError = false) { const el = $('#admin-notice'); el.textContent = message; el.classList.toggle('error', isError); el.classList.add('show'); clearTimeout(toastTimer); toastTimer = setTimeout(() => el.classList.remove('show'), 4000); }
  function empty(container, message) { container.replaceChildren(node('div', 'empty-admin', message)); }
  function formatDate(value) { if (!value) return 'Date not recorded'; try { return new Date(value).toLocaleString(); } catch (_) { return String(value); } }
  function esc(value) { return String(value ?? '').trim(); }

  async function request(path, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    const headers = { ...(options.headers || {}) };
    const isForm = options.body instanceof FormData;
    if (options.body && !isForm && !headers['Content-Type']) headers['Content-Type'] = 'application/json';
    if (state.csrf && !['GET', 'HEAD', 'OPTIONS'].includes(method)) headers['X-CSRF-Token'] = state.csrf;
    let response;
    try { response = await fetch(path, { credentials: 'same-origin', ...options, method, headers, cache: 'no-store' }); }
    catch (_) { throw new Error('Could not reach the server. Check that the application is running.'); }
    let data = {};
    try { data = await response.json(); } catch (_) { /* body may be empty */ }
    if (!response.ok) {
      if (response.status === 401 && state.authenticated && !path.endsWith('/login')) {
        state.authenticated = false; state.csrf = ''; showLogin('Your session expired. Sign in again.');
      }
      const error = new Error(data.detail || 'The request could not be completed.'); error.status = response.status; throw error;
    }
    return data;
  }

  function showLogin(message = '') {
    $('#login-screen').hidden = false; $('#dashboard-screen').hidden = true;
    state.authenticated = false;
    const msg = $('#login-message'); msg.textContent = message; msg.classList.toggle('error', Boolean(message));
    $('#login-form').elements.password.value = '';
  }
  function showDashboard(username) {
    state.authenticated = true; state.username = username || 'Administrator';
    $('#login-screen').hidden = true; $('#dashboard-screen').hidden = false;
    $('#sidebar-username').textContent = state.username;
    renderTab('overview');
  }

  async function startSession() {
    try {
      const session = await request('/api/admin/session');
      state.csrf = session.csrf_token || ''; showDashboard(session.username);
    } catch (_) { showLogin(); }
  }

  function metric(label, value, symbol) {
    const card = node('div', 'metric-card'); card.append(node('span', 'metric-symbol', symbol));
    const text = node('span'); text.append(node('strong', '', value), node('small', '', label)); card.append(text); return card;
  }
  function heading(title, description, actionLabel, action) {
    const row = node('div', 'page-heading-row'); const info = node('div'); info.append(node('h2', '', title)); if (description) info.append(node('p', '', description)); row.append(info);
    if (actionLabel) { const button = node('button', 'button button-primary', actionLabel); button.type = 'button'; button.addEventListener('click', action); row.append(button); }
    return row;
  }
  function quickAction(label, symbol, tab) {
    const button = node('button', 'quick-action'); button.type = 'button'; button.append(node('span', '', symbol), node('span', '', label)); button.addEventListener('click', () => renderTab(tab)); return button;
  }

  async function renderOverview() {
    const content = $('#admin-content'); content.replaceChildren(heading('Your portfolio, at a glance', 'Manage public information and respond to submissions from one place.'));
    const loading = node('div', 'loading-panel', 'Loading overview…'); content.append(loading);
    try {
      const counts = await request('/api/admin/dashboard');
      const grid = node('div', 'admin-grid');
      grid.append(metric('Published and draft education entries', counts.education, '⌂'), metric('Skill entries', counts.skills, '✳'), metric('Services', counts.services, '◈'), metric('Projects', counts.projects, '▣'), metric('Reviews awaiting moderation', counts.pending_reviews, '☆'), metric('Unread contact messages', counts.unread_messages, '✉'));
      const sections = node('div', 'overview-sections');
      const quick = node('section', 'admin-panel'); const quickHead = node('div', 'panel-heading'); quickHead.append(node('div')); quickHead.firstChild.append(node('h3', '', 'Quick actions'), node('p', '', 'Common portfolio management tasks')); quick.append(quickHead);
      const actions = node('div', 'quick-actions'); actions.append(quickAction('Update the site copy', '⚙', 'settings'), quickAction('Edit the CV', '▤', 'cv'), quickAction('Add a project', '+', 'projects'), quickAction('Moderate reviews', '☆', 'reviews'), quickAction('Review messages', '✉', 'messages'), quickAction('Edit education', '⌂', 'education')); quick.append(actions);
      const activity = node('section', 'admin-panel'); const activityHead = node('div', 'panel-heading'); activityHead.append(node('div')); activityHead.firstChild.append(node('h3', '', 'Recent administrative activity'), node('p', '', 'Latest saved changes')); activity.append(activityHead);
      const activityList = node('div', 'activity-list');
      try {
        const result = await request('/api/admin/audit');
        const items = (result.items || []).slice(0, 5);
        if (!items.length) activityList.append(node('p', 'subtle-text', 'No administrative activity has been recorded yet.'));
        items.forEach(item => { const row = node('div', 'activity-row'); row.append(node('i', 'activity-mark')); const text = node('div'); text.append(node('strong', '', item.action), node('small', '', `${item.entity_type || 'system'} · ${formatDate(item.created_at)}`)); row.append(text); activityList.append(row); });
      } catch (_) { activityList.append(node('p', 'subtle-text', 'Activity could not be loaded.')); }
      activity.append(activityList); sections.append(quick, activity);
      content.replaceChildren(heading('Your portfolio, at a glance', 'Manage public information and respond to submissions from one place.'), grid, sections);
      updateBadges(counts);
    } catch (error) { loading.textContent = error.message; }
  }
  function updateBadges(counts) {
    const pending = $('#pending-count'); pending.textContent = counts.pending_reviews || 0; pending.hidden = !(counts.pending_reviews > 0);
    const unread = $('#unread-count'); unread.textContent = counts.unread_messages || 0; unread.hidden = !(counts.unread_messages > 0);
  }

  async function renderSettings() {
    const content = $('#admin-content'); content.replaceChildren(heading('Site settings', 'Edit public-facing copy, identity, and contact information. Use only verified facts.'));
    const layout = node('div', 'settings-layout'); const form = node('form', 'settings-form'); form.id = 'settings-form';
    form.append(node('h3', '', 'Public website information'), node('p', '', 'These fields update the public website as soon as you save them. The public portfolio name and CV owner name stay separate.'));
    const fieldsWrap = node('div', 'settings-fields');
    try {
      const result = await request('/api/admin/settings'); const settings = result.settings || {};
      settingsFields.forEach(([key, label, type, wide]) => {
        const field = node('label', wide ? 'wide' : ''); field.append(node('span', '', label));
        let input;
        if (type === 'textarea') { input = node('textarea'); input.rows = key === 'about_text' || key === 'hero_description' ? 4 : 3; }
        else { input = node('input'); input.type = type; }
        input.name = key; input.maxLength = ({ portfolio_name: 100, cv_name: 100, browser_title: 180, meta_description: 300, tagline: 240, intro: 300, hero_description: 600, about_text: 3000, footer_text: 250, contact_email: 254, whatsapp_number: 60, location: 160 })[key] || 500;
        input.value = esc(settings[key]); field.append(input); fieldsWrap.append(field);
      });
      form.append(fieldsWrap); const submit = node('button', 'button button-primary settings-save', 'Save website settings ↗'); submit.type = 'submit'; form.append(submit);
      form.addEventListener('submit', async event => {
        event.preventDefault(); submit.disabled = true; const values = Object.fromEntries(new FormData(form).entries());
        try { await request('/api/admin/settings', { method: 'PUT', body: JSON.stringify({ settings: values }) }); toast('Website settings saved.'); notice('Settings saved. The public website will use the updated copy immediately.'); }
        catch (error) { notice(error.message, true); }
        finally { submit.disabled = false; }
      });
    } catch (error) { fieldsWrap.append(node('p', 'admin-message error', error.message)); }
    const help = node('aside', 'side-help'); help.append(node('h3', '', 'Keep your details accurate'), node('p', '', 'Avoid publishing private information or unverified qualifications.'), node('ul'));
    const tips = ['The public portfolio owner is Ahmed Shahid.', 'The CV owner is Ahmed Chai; it is intentionally separate.', 'The school is initially set to Cambridge World High School.', 'The original college name could not be confirmed from the unavailable reference site; add the verified name under Education.'];
    tips.forEach(tip => help.querySelector('ul').append(node('li', '', tip)));
    layout.append(form, help); content.append(layout);
  }

  function makeField(name, label, type, required, wide, value = '') {
    const wrap = node('label', wide ? 'wide' : ''); wrap.append(node('span', '', label));
    let input;
    if (type === 'textarea') { input = node('textarea'); input.rows = 4; }
    else { input = node('input'); input.type = type === 'number' ? 'number' : type; }
    input.name = name; input.value = value ?? ''; if (required) input.required = true;
    if (type === 'number') { input.min = '1'; input.max = '5'; input.step = '1'; }
    if (type === 'url') input.placeholder = 'https://…';
    if (name === 'image_url') input.placeholder = 'https://… or upload below';
    wrap.append(input); return wrap;
  }

  async function renderContentTab(kind) {
    const config = kinds[kind]; const content = $('#admin-content'); content.replaceChildren(heading(config.plural, `Add, edit, publish, reorder, and remove ${config.plural.toLowerCase()} entries. Changes are saved to the database.`, `+ Add ${config.label}`, () => openEditor(kind, null)));
    const list = node('div', 'item-list'); list.append(node('div', 'loading-panel', 'Loading content…')); content.append(list);
    try {
      const result = await request(`/api/admin/content/${kind}`); state.contentItems = result.items || []; renderManagedItems(kind, list, state.contentItems);
    } catch (error) { empty(list, error.message); }
  }

  function statusPill(label, kind = '') { return node('span', `state-pill ${kind}`, label); }
  function renderManagedItems(kind, wrap, items) {
    wrap.replaceChildren();
    if (!items.length) return empty(wrap, `No ${kinds[kind].plural.toLowerCase()} have been added yet. Use “Add ${kinds[kind].label}” to create the first entry.`);
    items.forEach(item => {
      const data = item.data || {}; const card = node('article', 'managed-item');
      card.append(node('span', 'managed-mark', ({ education: '⌂', skills: '✳', services: '◈', projects: '▣', reviews: '☆' })[kind]));
      const info = node('div', 'managed-info');
      const primary = data.title || data.institution || data.name || '(Untitled item)'; info.append(node('strong', '', primary));
      const summary = data.description || data.message || data.qualification || data.category || data.role || '';
      info.append(node('p', '', summary.slice(0, 230)));
      const meta = node('div', 'managed-meta');
      meta.append(statusPill(item.published ? 'Published' : 'Draft', item.published ? 'published' : ''), statusPill(`Order ${item.sort_order}`, ''));
      if (kind === 'reviews') meta.append(statusPill(item.moderation_status || 'pending', item.moderation_status || 'pending'));
      info.append(meta); card.append(info);
      const actions = node('div', 'managed-actions');
      if (kind === 'reviews' && item.moderation_status === 'pending') {
        const approve = node('button', 'mini-button primary', 'Approve'); approve.type = 'button'; approve.addEventListener('click', () => moderateReview(item, 'approved'));
        const reject = node('button', 'mini-button', 'Reject'); reject.type = 'button'; reject.addEventListener('click', () => moderateReview(item, 'rejected'));
        actions.append(approve, reject);
      }
      const edit = node('button', 'mini-button', 'Edit'); edit.type = 'button'; edit.addEventListener('click', () => openEditor(kind, item));
      const remove = node('button', 'mini-button danger', 'Delete'); remove.type = 'button'; remove.addEventListener('click', () => deleteItem(kind, item));
      actions.append(edit, remove); card.append(actions); wrap.append(card);
    });
  }

  async function moderateReview(item, status) {
    const label = status === 'approved' ? 'approve and publish' : 'reject';
    if (!window.confirm(`Are you sure you want to ${label} this review?`)) return;
    try {
      await request(`/api/admin/content/reviews/${item.id}`, { method: 'PUT', body: JSON.stringify({ data: item.data, published: status === 'approved', sort_order: item.sort_order, moderation_status: status }) });
      toast(status === 'approved' ? 'Review approved and published.' : 'Review rejected.'); renderContentTab('reviews');
    } catch (error) { notice(error.message, true); }
  }

  function openEditor(kind, item) {
    state.editorKind = kind; state.editorId = item ? item.id : null;
    const config = kinds[kind]; $('#editor-title').textContent = item ? `Edit ${config.label}` : `Add ${config.label}`;
    const fields = $('#editor-fields'); fields.replaceChildren(); const data = item?.data || {};
    config.fields.forEach(([key, label, type, required, wide]) => {
      const value = data[key] ?? (key === 'rating' ? 5 : ''); fields.append(makeField(key, label, type, required, wide, value));
    });
    if (kind === 'projects') {
      const uploadPanel = node('div', 'project-image-upload wide');
      uploadPanel.append(node('strong', '', 'Upload a project image'), node('p', '', 'Choose a JPG, PNG, or WebP up to 5 MB. The image is converted safely and its path is placed in the image field above.'));
      const file = node('input'); file.type = 'file'; file.accept = 'image/jpeg,image/png,image/webp'; file.setAttribute('aria-label', 'Project image file'); uploadPanel.append(file);
      const useImage = node('button', 'mini-button primary', 'Upload and use this image'); useImage.type = 'button'; uploadPanel.append(useImage);
      useImage.addEventListener('click', async () => {
        if (!file.files?.[0]) { toast('Choose an image file first.'); return; }
        useImage.disabled = true; const body = new FormData(); body.append('file', file.files[0]);
        try {
          const result = await request('/api/admin/project-image', { method: 'POST', body });
          const imageField = $('#editor-fields').querySelector('[name="image_url"]'); imageField.value = result.url;
          toast('Project image uploaded. Save the project to publish its new image.');
        } catch (error) { $('#editor-message').textContent = error.message; $('#editor-message').classList.add('error'); }
        finally { useImage.disabled = false; }
      });
      fields.append(uploadPanel);
    }
    const published = $('#content-editor-form').elements.published; published.checked = item ? Boolean(item.published) : kind !== 'reviews';
    $('#content-editor-form').elements.sort_order.value = item?.sort_order ?? 0;
    $('#moderation-field').hidden = kind !== 'reviews';
    $('#content-editor-form').elements.moderation_status.value = item?.moderation_status || (kind === 'reviews' ? 'pending' : 'approved');
    $('#editor-message').textContent = ''; $('#editor-message').classList.remove('error'); $('#editor-modal').hidden = false;
    const first = $('#editor-fields input, #editor-fields textarea'); if (first) first.focus();
  }
  function closeEditor() { $('#editor-modal').hidden = true; }

  async function saveEditor(event) {
    event.preventDefault(); const form = event.currentTarget; const kind = state.editorKind;
    const data = {};
    kinds[kind].fields.forEach(([key]) => { const field = form.querySelector(`[name="${key}"]`); if (!field) return; data[key] = field.value.trim(); if (key === 'rating') data[key] = Number(field.value); });
    const published = form.elements.published.checked; const sort_order = Number(form.elements.sort_order.value || 0);
    let moderation_status = kind === 'reviews' ? form.elements.moderation_status.value : 'approved';
    const finalPublished = kind === 'reviews' && moderation_status === 'approved' ? published : published;
    const message = $('#editor-message'); message.textContent = ''; message.classList.remove('error');
    const submit = $('button[type="submit"]', form); submit.disabled = true;
    try {
      const body = JSON.stringify({ data, published: finalPublished, sort_order, moderation_status });
      await request(state.editorId ? `/api/admin/content/${kind}/${state.editorId}` : `/api/admin/content/${kind}`, { method: state.editorId ? 'PUT' : 'POST', body });
      closeEditor(); toast(`${kinds[kind].label[0].toUpperCase()}${kinds[kind].label.slice(1)} saved.`); await renderContentTab(kind);
    } catch (error) { message.textContent = error.message; message.classList.add('error'); }
    finally { submit.disabled = false; }
  }

  async function deleteItem(kind, item) {
    const label = item.data?.title || item.data?.institution || item.data?.name || 'this item';
    if (!window.confirm(`Delete “${label}”? This cannot be undone.`)) return;
    try { await request(`/api/admin/content/${kind}/${item.id}`, { method: 'DELETE' }); toast('Item deleted.'); await renderContentTab(kind); }
    catch (error) { notice(error.message, true); }
  }

  function renderCvForm(content) {
    const form = node('form', 'settings-form'); form.id = 'cv-content-form';
    form.append(node('h3', '', 'Editable CV content'), node('p', '', 'The generated PDF uses these fields plus published Education, Skills, and Projects entries. Do not add unverified qualifications or experience.'));
    const fields = node('div', 'cv-fields');
    cvFields.forEach(([key, label, type, wide]) => {
      const field = makeField(key, label, type, false, wide, content[key] || '');
      const input = field.querySelector('input,textarea');
      input.maxLength = ({ headline: 140, summary: 3000, email: 254, phone: 60, location: 160, work_experience: 8000, certifications: 4000, achievements: 4000, additional_information: 4000 })[key];
      if (key === 'work_experience' || key === 'certifications' || key === 'achievements') input.placeholder = 'Add one verified entry per line';
      fields.append(field);
    });
    form.append(fields);
    const save = node('button', 'button button-primary settings-save', 'Save CV content ↗'); save.type = 'submit'; form.append(save);
    form.addEventListener('submit', async event => {
      event.preventDefault(); save.disabled = true; const values = Object.fromEntries(new FormData(form).entries());
      try { await request('/api/admin/cv', { method: 'PUT', body: JSON.stringify({ content: values }) }); toast('CV content saved.'); notice('CV saved. The generated PDF has been refreshed.'); }
      catch (error) { notice(error.message, true); }
      finally { save.disabled = false; }
    });
    return form;
  }

  async function renderCv() {
    const content = $('#admin-content'); content.replaceChildren(heading('CV & profile image', 'Update the profile photo and edit the CV. The CV owner name is separate from the public portfolio name.'));
    const grid = node('div', 'settings-layout'); const left = node('div'); const right = node('div');
    left.append(node('div', 'loading-panel', 'Loading CV content…')); grid.append(left, right); content.append(grid);
    try {
      const [cv, settings] = await Promise.all([request('/api/admin/cv'), request('/api/admin/settings')]);
      left.replaceChildren(renderCvForm(cv.content || {}));
      const profileCard = node('section', 'profile-card'); profileCard.append(node('h3', '', 'Profile picture'), node('p', '', 'Upload a JPG, PNG, or WebP file up to 5 MB. The server re-encodes it to WebP to remove embedded active content.'));
      const preview = node('div', 'profile-preview'); const img = node('img'); img.src = `/api/public/profile-image?v=${Date.now()}`; img.alt = 'Current profile image'; preview.append(img); profileCard.append(preview);
      const sx = Number(settings.settings?.profile_image_x); const sy = Number(settings.settings?.profile_image_y);
      const xValue = Number.isFinite(sx) && settings.settings?.profile_image_x !== undefined ? sx : 50;
      const yValue = Number.isFinite(sy) && settings.settings?.profile_image_y !== undefined ? sy : 27;
      img.style.objectPosition = `${xValue}% ${yValue}%`;
      const focusControls = node('div', 'profile-focus-controls');
      const xLabel = node('label'); xLabel.append(node('span', '', 'Horizontal focus')); const xRange = node('input'); xRange.type = 'range'; xRange.min = '0'; xRange.max = '100'; xRange.value = String(xValue); xRange.name = 'focus_x'; xLabel.append(xRange);
      const yLabel = node('label'); yLabel.append(node('span', '', 'Vertical focus')); const yRange = node('input'); yRange.type = 'range'; yRange.min = '0'; yRange.max = '100'; yRange.value = String(yValue); yRange.name = 'focus_y'; yLabel.append(yRange);
      const focusButton = node('button', 'mini-button primary', 'Save image position'); focusButton.type = 'button'; focusControls.append(xLabel, yLabel, focusButton); profileCard.append(focusControls);
      const changePreviewPosition = () => { img.style.objectPosition = `${xRange.value}% ${yRange.value}%`; };
      xRange.addEventListener('input', changePreviewPosition); yRange.addEventListener('input', changePreviewPosition);
      focusButton.addEventListener('click', async () => { focusButton.disabled = true; try { await request('/api/admin/profile-image/position', { method: 'PUT', body: JSON.stringify({ x: Number(xRange.value), y: Number(yRange.value) }) }); toast('Image position saved.'); notice('Profile image crop position updated on the public website.'); } catch (error) { notice(error.message, true); } finally { focusButton.disabled = false; } });
      const uploadForm = node('form', 'admin-form'); uploadForm.id = 'profile-upload-form';
      const label = node('label'); label.append(node('span', '', 'Choose new profile image')); const file = node('input'); file.type = 'file'; file.name = 'file'; file.accept = 'image/jpeg,image/png,image/webp'; file.required = true; label.append(file); uploadForm.append(label);
      const upload = node('button', 'button button-primary', 'Upload image ↗'); upload.type = 'submit'; uploadForm.append(upload);
      uploadForm.addEventListener('submit', async event => {
        event.preventDefault(); if (!file.files?.[0]) return; upload.disabled = true;
        const body = new FormData(); body.append('file', file.files[0]);
        try { await request('/api/admin/profile-image', { method: 'POST', body }); img.src = `/api/public/profile-image?v=${Date.now()}`; toast('Profile picture updated.'); notice('Profile picture updated on the public website.'); file.value = ''; }
        catch (error) { notice(error.message, true); }
        finally { upload.disabled = false; }
      });
      profileCard.append(uploadForm); const profileActions = node('div', 'profile-actions');
      const resetProfile = node('button', 'mini-button', 'Restore placeholder'); resetProfile.type = 'button'; resetProfile.addEventListener('click', async () => {
        if (!window.confirm('Restore the generated placeholder portrait?')) return;
        try { await request('/api/admin/profile-image/reset', { method: 'POST' }); img.src = `/api/public/profile-image?v=${Date.now()}`; xRange.value = '50'; yRange.value = '27'; changePreviewPosition(); toast('Placeholder restored.'); }
        catch (error) { notice(error.message, true); }
      }); profileActions.append(resetProfile); profileCard.append(profileActions); right.append(profileCard);
      const fileCard = node('section', 'profile-card'); fileCard.append(node('h3', '', 'Published CV PDF'), node('p', '', cv.uploaded ? 'A custom PDF is currently published. Upload a new PDF to replace it, or switch back to the editable generated CV.' : 'The downloadable PDF is generated from the editable CV fields and published entries.'));
      const link = node('a', 'mini-button primary', 'Download current CV PDF ↓'); link.href = '/api/public/cv.pdf'; link.target = '_blank'; link.rel = 'noopener noreferrer'; fileCard.append(link);
      const uploadCvForm = node('form', 'admin-form'); uploadCvForm.style.marginTop = '17px'; const cvLabel = node('label'); cvLabel.append(node('span', '', 'Replace with PDF (max 5 MB)')); const pdf = node('input'); pdf.type = 'file'; pdf.name = 'file'; pdf.accept = 'application/pdf,.pdf'; pdf.required = true; cvLabel.append(pdf); uploadCvForm.append(cvLabel); const uploadPdf = node('button', 'button button-secondary', 'Upload replacement PDF'); uploadPdf.type = 'submit'; uploadCvForm.append(uploadPdf);
      uploadCvForm.addEventListener('submit', async event => {
        event.preventDefault(); if (!pdf.files?.[0]) return; uploadPdf.disabled = true; const body = new FormData(); body.append('file', pdf.files[0]);
        try { await request('/api/admin/cv-upload', { method: 'POST', body }); toast('CV PDF replaced.'); notice('The new PDF is now published at the public CV download link.'); await renderCv(); }
        catch (error) { notice(error.message, true); }
        finally { uploadPdf.disabled = false; }
      }); fileCard.append(uploadCvForm);
      const resetPdf = node('button', 'mini-button', 'Use generated CV instead'); resetPdf.type = 'button'; resetPdf.style.marginTop = '10px'; resetPdf.addEventListener('click', async () => { if (!window.confirm('Switch the public download back to the editable generated CV?')) return; try { await request('/api/admin/cv/reset', { method: 'POST' }); toast('Generated CV restored.'); await renderCv(); } catch (error) { notice(error.message, true); } }); fileCard.append(resetPdf); right.append(fileCard);
      const tip = node('aside', 'side-help'); tip.append(node('h3', '', 'CV notes'), node('p', '', 'CV identity is configured as Ahmed Chai. The public portfolio name is Ahmed Shahid.')); const ul = node('ul'); ['Education, skills, and projects are reused from their corresponding content sections.', 'The school entry is prefilled as Cambridge World High School.', 'The source college name could not be verified from the reference website. Add the correct original name before publishing.', 'Keep personal contact details and achievements accurate.']; tip.append(ul); ['Education, skills, and projects are reused from their corresponding content sections.', 'The school entry is prefilled as Cambridge World High School.', 'The source college name could not be verified from the reference website. Add the correct original name before publishing.', 'Keep personal contact details and achievements accurate.'].forEach(x => ul.append(node('li', '', x))); right.append(tip);
    } catch (error) { left.replaceChildren(node('p', 'admin-message error', error.message)); }
  }

  async function renderMessages() {
    const content = $('#admin-content'); content.replaceChildren(heading('Contact messages', 'Private form submissions are only accessible from this signed-in dashboard.'));
    const list = node('div', 'item-list'); list.append(node('div', 'loading-panel', 'Loading inbox…')); content.append(list);
    try {
      const result = await request('/api/admin/contacts'); const items = result.items || []; list.replaceChildren();
      if (!items.length) return empty(list, 'Your inbox is empty. New messages from the public contact form will appear here.');
      items.forEach(item => {
        const card = node('article', 'message-card'); const top = node('div', 'message-card-top'); const heading = node('div'); heading.append(node('h3', '', item.name), node('a', 'message-email', item.email)); heading.querySelector('a').href = `mailto:${item.email}`; top.append(heading); const meta = node('div'); meta.append(node('time', '', formatDate(item.created_at)), statusPill(item.status, item.status)); top.append(meta); card.append(top);
        if (item.subject) card.append(node('p', '', `Subject: ${item.subject}`)); card.append(node('p', 'message-body', item.message));
        const bottom = node('div', 'message-card-bottom'); bottom.append(node('small', 'subtle-text', `Message #${item.id}`)); const actions = node('div', 'message-actions');
        const select = node('select', 'admin-select'); select.setAttribute('aria-label', 'Message status'); ['unread', 'read', 'resolved'].forEach(status => { const opt = node('option', '', status[0].toUpperCase() + status.slice(1)); opt.value = status; opt.selected = item.status === status; select.append(opt); });
        const save = node('button', 'mini-button primary', 'Save status'); save.type = 'button'; save.addEventListener('click', async () => { save.disabled = true; try { await request(`/api/admin/contacts/${item.id}`, { method: 'PATCH', body: JSON.stringify({ status: select.value }) }); toast('Message status updated.'); await renderMessages(); } catch (error) { notice(error.message, true); } finally { save.disabled = false; } });
        const remove = node('button', 'mini-button danger', 'Delete'); remove.type = 'button'; remove.addEventListener('click', async () => { if (!window.confirm('Permanently delete this contact message?')) return; try { await request(`/api/admin/contacts/${item.id}`, { method: 'DELETE' }); toast('Message deleted.'); await renderMessages(); } catch (error) { notice(error.message, true); } });
        actions.append(select, save, remove); bottom.append(actions); card.append(bottom); list.append(card);
      });
    } catch (error) { empty(list, error.message); }
  }

  async function renderAudit() {
    const content = $('#admin-content'); content.replaceChildren(heading('Audit log', 'Recent administrator actions. Passwords and secret tokens are never included.'));
    const wrap = node('div', 'audit-table-wrap'); wrap.append(node('div', 'loading-panel', 'Loading audit events…')); content.append(wrap);
    try {
      const result = await request('/api/admin/audit'); const items = result.items || []; wrap.replaceChildren();
      if (!items.length) return empty(wrap, 'No audit events have been recorded yet.');
      const table = node('table', 'audit-table'); const thead = node('thead'); const tr = node('tr'); ['Time', 'Actor', 'Action', 'Entity', 'Details'].forEach(x => tr.append(node('th', '', x))); thead.append(tr); table.append(thead); const tbody = node('tbody');
      items.forEach(item => { const row = node('tr'); row.append(node('td', '', formatDate(item.created_at)), node('td', '', item.actor), node('td', '', item.action), node('td', '', `${item.entity_type || '—'} ${item.entity_id ? `#${item.entity_id}` : ''}`), node('td', '', JSON.stringify(item.details || {}))); tbody.append(row); });
      table.append(tbody); wrap.append(table);
    } catch (error) { empty(wrap, error.message); }
  }

  async function renderTab(tab) {
    if (!titles[tab]) tab = 'overview'; state.tab = tab;
    $('#view-title').textContent = titles[tab];
    document.querySelectorAll('.admin-nav-item[data-tab]').forEach(button => button.classList.toggle('active', button.dataset.tab === tab));
    $('#admin-sidebar').classList.remove('open');
    if (tab === 'overview') return renderOverview();
    if (tab === 'settings') return renderSettings();
    if (kinds[tab]) return renderContentTab(tab);
    if (tab === 'cv') return renderCv();
    if (tab === 'messages') return renderMessages();
    if (tab === 'audit') return renderAudit();
  }

  $('#login-form').addEventListener('submit', async event => {
    event.preventDefault(); const form = event.currentTarget; const submit = $('button[type="submit"]', form); const message = $('#login-message'); submit.disabled = true; message.textContent = ''; message.classList.remove('error');
    const payload = Object.fromEntries(new FormData(form).entries());
    try { const result = await request('/api/admin/login', { method: 'POST', body: JSON.stringify(payload) }); state.csrf = result.csrf_token || ''; showDashboard(result.username); toast('Signed in securely.'); }
    catch (error) { message.textContent = error.status === 429 ? 'Too many sign-in attempts. Try again later.' : 'Unable to sign in with those credentials.'; message.classList.add('error'); }
    finally { submit.disabled = false; form.elements.password.value = ''; }
  });
  $('#logout-button').addEventListener('click', async () => {
    try { await request('/api/admin/logout', { method: 'POST', body: '{}' }); } catch (_) { /* session may already have expired */ }
    state.csrf = ''; state.authenticated = false; showLogin('You have signed out.');
  });
  $('#admin-nav').addEventListener('click', event => { const button = event.target.closest('button[data-tab]'); if (button) renderTab(button.dataset.tab); });
  $('#sidebar-toggle').addEventListener('click', () => $('#admin-sidebar').classList.toggle('open'));
  $('#content-editor-form').addEventListener('submit', saveEditor);
  $('#modal-close').addEventListener('click', closeEditor); $('#modal-cancel').addEventListener('click', closeEditor);
  $('#editor-modal').addEventListener('click', event => { if (event.target === $('#editor-modal')) closeEditor(); });
  document.addEventListener('keydown', event => { if (event.key === 'Escape') { closeEditor(); $('#admin-sidebar').classList.remove('open'); } });
  startSession();
})();
