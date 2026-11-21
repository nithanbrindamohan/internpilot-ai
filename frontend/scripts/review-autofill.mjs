/** InternPilot review-first form assist. No submit clicks, no CAPTCHA bypass, no credentials. */
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline/promises';
import { stdin as input, stdout as output } from 'node:process';
import { chromium } from '@playwright/test';

const [packetPath, ...argv] = process.argv.slice(2);
if (!packetPath) {
  console.error('Usage: node scripts/review-autofill.mjs <downloaded-packet.json> [--resume <resume.pdf>]');
  process.exit(1);
}
const resumeFlag = argv.indexOf('--resume');
const resumePath = resumeFlag >= 0 ? argv[resumeFlag + 1] : undefined;
const packet = JSON.parse(fs.readFileSync(path.resolve(packetPath), 'utf8'));
const target = new URL(packet.apply_url);
if (target.protocol !== 'https:' || target.username || target.password) throw new Error('Only HTTPS application links are allowed.');
const applicant = packet.candidate || {};
const answers = packet.answers || {};
const rl = readline.createInterface({ input, output });
const browser = await chromium.launch({ headless: false });
const page = await browser.newPage();

async function fillFirst(selectors, value) {
  if (!value || typeof value !== 'string') return false;
  for (const selector of selectors) {
    try {
      const field = page.locator(selector).first();
      if (await field.count() && await field.isVisible() && await field.isEnabled()) {
        const type = await field.getAttribute('type');
        if (['hidden','file','checkbox','radio','submit'].includes(type)) continue;
        await field.fill(value, { timeout: 1200 });
        return true;
      }
    } catch { /* Selector does not exist or is a custom widget. */ }
  }
  return false;
}
const fields = [
  ['Full name', applicant.full_name, ['input[name="name"]','input[name="full_name"]','input[id="name"]']],
  ['First name', (applicant.full_name||'').split(' ')[0], ['input[name="first_name"]','input[id*="first_name"]','input[autocomplete="given-name"]']],
  ['Last name', (applicant.full_name||'').split(' ').slice(1).join(' '), ['input[name="last_name"]','input[id*="last_name"]','input[autocomplete="family-name"]']],
  ['Email', applicant.email, ['input[type="email"]','input[name="email"]','input[autocomplete="email"]']],
  ['Phone', answers.Phone, ['input[type="tel"]','input[name*="phone"]','input[autocomplete="tel"]']],
  ['LinkedIn', answers.LinkedIn, ['input[name*="linkedin" i]','input[id*="linkedin" i]']],
  ['Portfolio / GitHub', answers['Portfolio / GitHub'], ['input[name*="github" i]','input[name*="portfolio" i]']],
  ['Cover letter', packet.cover_letter, ['textarea[name*="cover_letter" i]','textarea[id*="cover_letter" i]','textarea[name*="coverletter" i]']],
];
try {
  console.log(`Opening ${target.origin}. Confirm this is the official employer application page.`);
  await page.goto(target.toString(), { waitUntil: 'domcontentloaded', timeout: 45000 });
  await rl.question('\nNavigate to the actual application form in the browser, then press Enter here to fill common fields...');
  let filled = [];
  for (const [name,value,selectors] of fields) if (await fillFirst(selectors,value)) filled.push(name);
  if (resumePath) {
    const file = path.resolve(resumePath);
    if (!fs.statSync(file).isFile()) throw new Error('Resume path is not a file.');
    const fileInput = page.locator('input[type="file"]').first();
    if (await fileInput.count()) {
      await fileInput.setInputFiles(file);
      filled.push('Resume attached');
    } else console.log('No standard file upload field found. Upload your resume manually.');
  }
  console.log('\nFilled:',filled.length ? filled.join(', ') : 'No matching standard fields found.');
  console.log('REVIEW all fields, required questions, attachments, and legal statements.');
  console.log('The helper NEVER clicks Submit. You must submit yourself.');
  await rl.question('Browser remains open for your review. Press Enter here ONLY when you are done to close it...');
} finally { await browser.close(); rl.close(); }
