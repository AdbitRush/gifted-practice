// Question-bank checker for index.html (Node built-ins only): node tools/check-questions.mjs [file]
// Fails (exit 1) on structural errors; prints arithmetic-sequence answers that disagree with the stored answer for a human to review.
import fs from 'node:fs';
import vm from 'node:vm';

const file = process.argv[2] || new URL('../index.html', import.meta.url);
const html = fs.readFileSync(file, 'utf8');
const grab = (start, end) => { const i = html.indexOf(start); if (i < 0) throw new Error(`missing ${start}`); return html.slice(i, html.indexOf(end, i) + end.length); };
const ctx = {};
vm.runInNewContext(`${grab('const TOPICS', '};')}\n${grab('const QUESTIONS=[', '}];')}\nthis.TOPICS=TOPICS;this.QUESTIONS=QUESTIONS;`, ctx);
const { TOPICS, QUESTIONS } = ctx;

const errors = [], review = [];
const ids = new Set();
const strip = (s) => String(s).replace(/<[^>]+>/g, '').trim();
for (const q of QUESTIONS) {
  const where = `${q.id || '(no id)'}`;
  if (!q.id || ids.has(q.id)) errors.push(`${where}: missing or duplicate id`);
  ids.add(q.id);
  if (!TOPICS[q.topic]) errors.push(`${where}: unknown topic ${q.topic}`);
  if (!Array.isArray(q.options) || q.options.length !== 4) errors.push(`${where}: needs exactly 4 options`);
  else if (new Set(q.options.map(strip)).size !== 4) errors.push(`${where}: duplicate options ${JSON.stringify(q.options)}`);
  if (!Number.isInteger(q.correct) || q.correct < 0 || q.correct > 3) errors.push(`${where}: correct index ${q.correct} out of range`);
  for (const k of ['q', 'explain', 'hint']) if (!strip(q[k] || '')) errors.push(`${where}: empty ${k}`);
  // number sequences "a, b, c, __": constant difference or constant ratio -> expected next term
  const m = strip(q.q).match(/((?:-?\d+\s*,\s*){2,}-?\d+)\s*,\s*_+\s*$/);
  if (m && q.topic === 'numbers') {
    const t = m[1].split(',').map((x) => Number(x.trim()));
    const d = t.slice(1).map((x, i) => x - t[i]);
    const r = t.slice(1).map((x, i) => (t[i] ? x / t[i] : NaN));
    let exp = null;
    if (d.every((x) => x === d[0])) exp = t.at(-1) + d[0];
    else if (r.every((x) => x === r[0] && Number.isInteger(x))) exp = t.at(-1) * r[0];
    const got = Number(strip(q.options?.[q.correct] ?? ''));
    if (exp !== null && got !== exp) review.push(`${where}: ${m[1]} -> simple rule gives ${exp}, stored answer is ${got} (check the intended rule)`);
    if (exp !== null && q.options && !q.options.map((o) => Number(strip(o))).includes(exp)) review.push(`${where}: the simple-rule answer ${exp} is not among the options`);
  }
}
const byTopic = {};
for (const q of QUESTIONS) byTopic[q.topic] = (byTopic[q.topic] || 0) + 1;
const pos = [0, 0, 0, 0];
for (const q of QUESTIONS) pos[q.correct] = (pos[q.correct] || 0) + 1;
console.log(`questions: ${QUESTIONS.length}; per topic ${JSON.stringify(byTopic)}; correct-answer position counts א-ד ${JSON.stringify(pos)}`);
for (const r of review) console.log('REVIEW', r);
for (const e of errors) console.log('ERROR', e);
console.log(errors.length ? `FAILED: ${errors.length} structural error(s)` : 'OK: no structural errors');
process.exit(errors.length ? 1 : 0);
