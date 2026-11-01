import { test, expect } from '@playwright/test';

// Every API response is mocked in the browser. No real database, API key,
// user account, invitation code, or employer is contacted by these tests.
const API = 'http://127.0.0.1:8000';
const user = {
  id: 1, full_name: 'Test Student', email: 'test@example.com',
  university: '', program: 'Software Engineering', graduation_year: '2028',
  location: 'Toronto, Ontario', work_authorization: '',
  skills: ['Python', 'React'], has_resume: false
};
const job = {
  id: 'job-001', company: 'Example Company', source: 'Greenhouse',
  title: 'Software Engineer Intern', location: 'Toronto, Ontario',
  url: 'https://example.com/jobs/001', match_score: 92,
};
const reply = (route, body, status = 200) => route.fulfill({
  status, contentType: 'application/json',
  headers: { 'access-control-allow-origin': '*' }, body: JSON.stringify(body)
});

async function mockApi(page, options = {}) {
  const state = { user: { ...user }, jobs: options.jobs ?? [job], applications: [], seen: [] };
  await page.route(`${API}/api/**`, async route => {
    const req = route.request(), url = new URL(req.url()), path = url.pathname;
    const method = req.method();
    state.seen.push(`${method} ${path}`);
    if (path === '/api/auth/register' && method === 'POST') {
      const data = req.postDataJSON();
      if (data.invite_code !== 'IP-TEST-CODE-1234') return reply(route, { detail: 'Invalid invitation code' }, 403);
      return reply(route, { access_token: 'fake-browser-test-token', token_type: 'bearer', user: state.user });
    }
    if (path === '/api/auth/login' && method === 'POST') {
      const data = req.postDataJSON();
      if (data.password !== 'TestPassword123!') return reply(route, { detail: 'Email or password is incorrect.' }, 401);
      return reply(route, { access_token: 'fake-browser-test-token', token_type: 'bearer', user: state.user });
    }
    if (path === '/api/profile' && method === 'GET') return reply(route, state.user);
    if (path === '/api/profile' && method === 'PUT') {
      state.user = { ...state.user, ...req.postDataJSON() };
      return reply(route, state.user);
    }
    if (path === '/api/profile/resume' && method === 'POST') {
      state.user.has_resume = true;
      return reply(route, { message: 'Resume uploaded and text extracted.', filename: 'resume.txt', characters: 30 });
    }
    if (path === '/api/jobs' && method === 'GET') return reply(route, state.jobs);
    if (path === '/api/discover/status' && method === 'GET') return reply(route, {
      configured_sources: 2, checked_sources: 2, healthy_sources: 2, active_jobs: state.jobs.length
    });
    if (path === '/api/discover' && method === 'POST') return reply(route, {
      status: 'completed', message: 'Discovery complete.', found: 2, relevant: 1,
      configured_sources: 2, successful_sources: 2, errors: []
    });
    if (path === '/api/applications' && method === 'GET') return reply(route, state.applications);
    if (path === '/api/applications' && method === 'POST') {
      state.applications.push({ id: state.applications.length + 1, ...req.postDataJSON(),
        company: job.company, title: job.title, url: job.url, status: 'draft' });
      return reply(route, { id: state.applications.length, status: 'draft' });
    }
    if (/^\/api\/applications\/\d+$/.test(path) && method === 'PATCH') {
      const app = state.applications.find(a => a.id === Number(path.split('/').at(-1)));
      if (app) app.status = req.postDataJSON().status;
      return reply(route, { id: app?.id, status: app?.status });
    }
    if (path.endsWith('/ai-match') && method === 'POST') return reply(route, {
      score: 93, explanation: 'Good match for Python and React experience.',
      matched_skills: ['Python', 'React'], missing_skills: ['Docker']
    });
    if (path.endsWith('/cover-letter') && method === 'POST') return reply(route, {
      cover_letter: 'Dear Hiring Team, I am applying for the Software Engineer Intern role.'
    });
    return reply(route, { detail: `Unmocked endpoint: ${method} ${path}` }, 404);
  });
  return state;
}

async function login(page) {
  await page.goto('/');
  await page.getByLabel('Email').fill('test@example.com');
  await page.getByLabel('Password').fill('TestPassword123!');
  await page.getByRole('button', { name: 'Sign in', exact: true }).last().click();
  await expect(page.getByRole('heading', { name: 'Your student profile' })).toBeVisible();
}

test('registration requires a valid invitation code', async ({ page }) => {
  const state = await mockApi(page);
  await page.goto('/');
  await page.getByRole('button', { name: 'Create an account' }).click();
  await page.getByLabel('Invitation code').fill('INVALID-CODE');
  await page.getByLabel('Full name').fill('Test Student');
  await page.getByLabel('Email').fill('test@example.com');
  await page.getByLabel('Password').fill('TestPassword123!');
  await page.getByRole('button', { name: 'Create free account' }).click();
  await expect(page.getByText('Invalid invitation code')).toBeVisible();
  await page.getByLabel('Invitation code').fill('IP-TEST-CODE-1234');
  await page.getByRole('button', { name: 'Create free account' }).click();
  await expect(page.getByRole('heading', { name: 'Your student profile' })).toBeVisible();
  expect(state.seen.filter(x => x === 'POST /api/auth/register')).toHaveLength(2);
});

test('login, logout and session navigation', async ({ page }) => {
  await mockApi(page);
  await login(page);
  await expect(page.getByText('Example Company')).toBeVisible();
  await page.getByRole('button', { name: 'Sign out' }).click();
  await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible();
});

test('profile edits persist in mocked API and resume upload works', async ({ page }) => {
  const state = await mockApi(page);
  await login(page);
  await page.getByLabel('University / institution').fill('Example University');
  await page.getByLabel('Skills (comma separated)').fill('Python, React, SQL');
  await page.getByRole('button', { name: 'Save profile' }).click();
  await expect(page.getByText('Your profile was saved.')).toBeVisible();
  expect(state.user.university).toBe('Example University');
  expect(state.user.skills).toEqual(['Python', 'React', 'SQL']);
  await page.locator('input[type=file]').setInputFiles({
    name: 'resume.txt', mimeType: 'text/plain', buffer: Buffer.from('Software engineering student, Python')
  });
  await page.getByRole('button', { name: 'Upload resume' }).click();
  await expect(page.getByText(/Resume uploaded and text extracted/)).toBeVisible();
  expect(state.user.has_resume).toBe(true);
});

test('job discovery, AI analysis, cover letter and application tracking', async ({ page }) => {
  const state = await mockApi(page);
  await login(page);
  await page.getByRole('button', { name: 'Discover internships' }).click();
  await expect(page.getByText(/Discovery complete/)).toBeVisible();
  await page.getByRole('button', { name: 'Prepare application' }).click();
  await page.getByRole('button', { name: 'AI match' }).click();
  await expect(page.getByText('AI fit score: 93%')).toBeVisible();
  await page.getByRole('button', { name: 'Generate cover letter' }).click();
  await expect(page.getByRole('textbox', { name: 'Cover letter draft' })).toHaveValue(/Dear Hiring Team/);
  await page.getByRole('button', { name: 'Save to my applications' }).click();
  await expect(page.getByText('Example Company · draft')).toBeVisible();
  expect(state.applications).toHaveLength(1);
  await page.locator('article.compact select').selectOption('ready_for_review');
  await expect(page.getByText('Example Company · ready_for_review')).toBeVisible();
});
