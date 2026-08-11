/**
 * NestLonger form handler.
 *
 * Runs on a Cloudflare Worker route bound to the site's own hostname, so the
 * marketing pages post same-origin. No third-party form service, no CORS, and no
 * client-side JavaScript is needed to submit - these are plain <form> POSTs and
 * the Worker answers with a 303 redirect.
 *
 * Routes:
 *   POST /api/lead       families        -> leads
 *   POST /api/partner    contractors     -> partners
 *   POST /api/subscribe  newsletter      -> subscribers
 *
 * Bindings:  DB (D1: nestlonger-leads)
 * Secrets:   SLACK_WEBHOOK_URL (optional), IP_SALT (optional)
 *
 * Deliberately no CAPTCHA: Turnstile would reintroduce the third-party script this
 * whole setup exists to remove. Spam is handled by a honeypot plus per-IP rate
 * limiting, which is proportionate until real spam shows up.
 */

const SITE = 'https://www.nestlonger.com';
const THANKS = `${SITE}/thanks.html`;

// Rate limit: submissions allowed per IP per window.
const RATE_LIMIT_MAX = 5;
const RATE_LIMIT_WINDOW_MIN = 60;

// `type` is echoed back on the thanks.html redirect so GA4 can tell a family lead
// apart from a newsletter signup. Without it every conversion looks identical.
const FORMS = {
  '/api/lead': {
    table: 'leads',
    required: ['name', 'email', 'zip'],
    fields: ['source', 'name', 'email', 'phone', 'zip', 'need', 'who', 'details'],
    label: 'New family lead',
    type: 'lead',
  },
  '/api/partner': {
    table: 'partners',
    required: ['business', 'contact', 'email'],
    fields: ['business', 'contact', 'email', 'phone', 'trade', 'coverage', 'license', 'aging_experience'],
    label: 'New partner application',
    type: 'partner',
  },
  '/api/subscribe': {
    table: 'subscribers',
    required: ['email'],
    fields: ['email', 'source'],
    label: 'New newsletter signup',
    type: 'newsletter',
  },
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const config = FORMS[url.pathname];

    if (!config) return new Response('Not found', { status: 404 });
    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405, headers: { Allow: 'POST' } });
    }

    let form;
    try {
      form = await request.formData();
    } catch {
      return problem('We could not read that submission. Please try again.');
    }

    // Honeypot. A real person never sees this field; bots fill every input they find.
    // Answer with the ordinary redirect so the bot cannot tell it was rejected.
    if ((form.get('website') || '').trim() !== '') {
      return redirectToThanks(config.type);
    }

    const values = {};
    for (const field of config.fields) {
      const v = (form.get(field) || '').toString().trim();
      values[field] = v ? v.slice(0, 2000) : null;
    }

    const missing = config.required.filter((f) => !values[f]);
    if (missing.length) {
      return problem(`Please fill in: ${missing.join(', ')}.`);
    }
    if (values.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email)) {
      return problem('That email address does not look right.');
    }

    const ip = request.headers.get('CF-Connecting-IP') || '';
    const ipHash = await hashIp(ip, env.IP_SALT);
    const createdAt = new Date().toISOString();

    if (await isRateLimited(env, ipHash)) {
      return problem('That is a lot of submissions in a short time. Please try again later.');
    }

    // Store first, notify second, but never let one failure swallow the lead: if the
    // insert fails we still try Slack, and only report an error if both paths failed.
    let stored = false;
    try {
      const cols = ['created_at', ...config.fields];
      const vals = [createdAt, ...config.fields.map((f) => values[f])];
      if (config.table !== 'subscribers') {
        cols.push('ip_hash', 'user_agent');
        vals.push(ipHash, (request.headers.get('User-Agent') || '').slice(0, 300));
      } else {
        cols.push('ip_hash');
        vals.push(ipHash);
      }
      const placeholders = cols.map(() => '?').join(', ');
      const sql = `INSERT INTO ${config.table} (${cols.join(', ')}) VALUES (${placeholders})`;
      await env.DB.prepare(sql).bind(...vals).run();
      stored = true;
      await recordSubmission(env, ipHash, createdAt);
    } catch (err) {
      // A duplicate newsletter email hits the UNIQUE constraint. That is a success
      // from the subscriber's point of view, not an error.
      if (config.table === 'subscribers' && String(err).includes('UNIQUE')) {
        return redirectToThanks(config.type);
      }
      console.error('D1 insert failed', String(err));
    }

    const notified = await notifySlack(env, config.label, values, createdAt);

    if (!stored && !notified) {
      return problem('Something went wrong on our end and your details were not saved. Please try again.');
    }

    return redirectToThanks(config.type);
  },
};

function redirectToThanks(type) {
  // 303 so the browser follows with GET rather than re-POSTing. The type rides
  // along so thanks.html can fire a distinct GA4 conversion event per form.
  const url = type ? `${THANKS}?type=${encodeURIComponent(type)}` : THANKS;
  return Response.redirect(url, 303);
}

function problem(message) {
  const body = `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex"><title>Something went wrong - NestLonger</title>
<link rel="stylesheet" href="/assets/styles.css"></head><body>
<section class="nl-form-page"><div class="nl-form-inner nl-thanks">
<h1 class="nl-form-h1">That didn't go through.</h1>
<p class="nl-form-lede">${escapeHtml(message)}</p>
<div class="nl-404-actions"><a href="/get-matched.html" class="nl-btn nl-btn-primary">Back to the form</a></div>
</div></section></body></html>`;
  return new Response(body, { status: 400, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

async function hashIp(ip, salt) {
  if (!ip) return null;
  const data = new TextEncoder().encode(`${salt || 'nestlonger'}:${ip}`);
  const digest = await crypto.subtle.digest('SHA-256', data);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('').slice(0, 32);
}

async function isRateLimited(env, ipHash) {
  if (!ipHash) return false;
  try {
    const cutoff = new Date(Date.now() - RATE_LIMIT_WINDOW_MIN * 60_000).toISOString();
    const row = await env.DB.prepare(
      'SELECT COUNT(*) AS n FROM rate_limit WHERE ip_hash = ? AND created_at > ?'
    ).bind(ipHash, cutoff).first();
    return (row?.n || 0) >= RATE_LIMIT_MAX;
  } catch {
    return false; // Never block a real lead because the rate-limit check itself broke.
  }
}

async function recordSubmission(env, ipHash, createdAt) {
  if (!ipHash) return;
  try {
    const cutoff = new Date(Date.now() - RATE_LIMIT_WINDOW_MIN * 60_000).toISOString();
    await env.DB.batch([
      env.DB.prepare('INSERT INTO rate_limit (ip_hash, created_at) VALUES (?, ?)').bind(ipHash, createdAt),
      env.DB.prepare('DELETE FROM rate_limit WHERE created_at < ?').bind(cutoff),
    ]);
  } catch (err) {
    console.error('rate_limit write failed', String(err));
  }
}

async function notifySlack(env, label, values, createdAt) {
  if (!env.SLACK_WEBHOOK_URL) return false;
  const lines = Object.entries(values)
    .filter(([, v]) => v)
    .map(([k, v]) => `*${k}:* ${v}`)
    .join('\n');
  try {
    const res = await fetch(env.SLACK_WEBHOOK_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: `:house: *${label}* - ${createdAt}\n${lines}` }),
    });
    return res.ok;
  } catch (err) {
    console.error('Slack notify failed', String(err));
    return false;
  }
}
