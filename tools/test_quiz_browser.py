"""Browser test for index.html (Python Playwright, Chromium, headless): python tools/test_quiz_browser.py [path-to-index.html]
Plays one full exam: answers alternately right and wrong, checks the feedback marks the right buttons, and reports where the correct answer appeared on screen."""
import pathlib
import sys
from collections import Counter

from playwright.sync_api import sync_playwright

page_file = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent / 'index.html').resolve()
errors, positions, checked = [], Counter(), 0
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    pg.goto(page_file.as_uri())
    pg.click('#btn-start')
    pg.click('#btn-prep-go')
    total = pg.evaluate('S.qs.length')
    for n in range(total):
        if pg.is_visible('#btn-half-go'):
            pg.click('#btn-half-go')
        info = pg.evaluate('(() => { const q = S.qs[S.idx]; return {id: q.id, correct: q.correct, ord: (S.order || {})[q.id] || null}; })()')
        btns = pg.query_selector_all('#answers .ans')
        assert len(btns) == 4, info
        shown = [int(x.get_attribute('data-orig')) if x.get_attribute('data-orig') is not None else i for i, x in enumerate(btns)]
        pos = shown.index(info['correct'])
        positions[pos] += 1
        if n % 2 == 0:
            btns[pos].click()
            assert 'correct' in (btns[pos].get_attribute('class') or ''), ('right answer not marked correct', info)
        else:
            wrong = (pos + 1) % 4
            btns[wrong].click()
            assert 'wrong' in (btns[wrong].get_attribute('class') or ''), ('wrong answer not marked', info)
            assert 'reveal' in (btns[pos].get_attribute('class') or ''), ('correct answer not revealed', info)
        checked += 1
        if pg.is_visible('#btn-next'):
            pg.click('#btn-next')
    score = pg.evaluate('S.correct')
    b.close()
print(f'file: {page_file.name}; questions answered: {checked}; score {score} (expected {(checked + 1) // 2})')
print('on-screen position of the correct answer (1st,2nd,3rd,4th):', [positions[i] for i in range(4)])
print('page errors:', errors or 'none')
ok = checked == total and score == (checked + 1) // 2 and not errors
print('PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)
