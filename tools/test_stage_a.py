from playwright.sync_api import sync_playwright
from pathlib import Path
import json,os
ROOT=Path(__file__).resolve().parents[1]; OUT=Path(os.environ.get('STAGE_A_QA_OUT','/downloads/gifted-stage-a-qa')); OUT.mkdir(exist_ok=True)
URL=os.environ.get('STAGE_A_QA_URL',(ROOT/'stage-a.html').as_uri())
logs=[]
def test(name,ok):
 assert ok,name
 logs.append(name)
def fits(page,name):
 test(name+' horizontal fit',page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
def shot(page,name):page.screenshot(path=str(OUT/(name+'.png')),full_page=True)
with sync_playwright() as p:
 b=p.chromium.launch(headless=True)
 page=b.new_page(viewport={'width':1280,'height':900}); errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(URL)
 data=page.evaluate('STAGE_A_TEST.data')
 test('5 passages',len(data['passages'])==5)
 test('line counts 8/12/16/20/24',[len(x['lines']) for x in data['passages']]==[8,12,16,20,24])
 test('25 reading questions',sum(len(x['questions']) for x in data['passages'])==25)
 test('25 math questions',len(data['math'])==25)
 for passage in data['passages']:
  for q in passage['questions']:
   test('reading answer options unique',len(q['options'])==4 and len(set(q['options']))==4)
   test('reading key valid',0<=q['correct']<4)
 for q in data['math']:
  test(q['id']+' key passes',page.evaluate('q=>STAGE_A_TEST.grade(q,q.answer)',q))
 # Independent expected sets, including boundaries and alternative valid answers.
 ranges={'m16':range(14,100),'m17':range(0,7),'m18':range(0,12),'m19':range(5,100),'m20':range(0,7)}
 for q in data['math']:
  if q['id'] in ranges:
   vals=page.evaluate('q=>Array.from({length:102},(_,i)=>i-1).filter(n=>STAGE_A_TEST.grade(q,n))',q)
   test(q['id']+' full domain matches independent oracle',vals==list(ranges[q['id']]))
 for bad in ['', ' ', '1.5','NaN','Infinity','2e1','12x','<script>']:
  test('reject malformed '+bad,page.evaluate('x=>STAGE_A_TEST.parseNumber(x)===null',bad))
 # Every reading passage through real UI, mixed deliberately wrong and right.
 for pi,passage in enumerate(data['passages']):
  page.goto(URL);page.locator('#test').click();page.select_option('#pick',passage['id']);page.locator('#start').click()
  test('test mode no hints',page.locator('#hint').count()==0)
  for i,q in enumerate(passage['questions']):
   option=q['correct'] if i!=1 else (q['correct']+1)%4
   page.locator(f'[data-option="{option}"]').click()
   test('no feedback before submit',page.locator('.feedback').count()==0)
   if i==0:
    order=page.locator('.option').all_text_contents();page.locator('#next').click();page.locator('#prev').click()
    test('stable answer order',page.locator('.option').all_text_contents()==order)
    test('answer survives back',page.locator(f'[data-option="{option}"]').get_attribute('aria-pressed')=='true')
   page.locator('#next').click()
  page.locator('#finish').click();test('reading result 4/5','4 מתוך 5' in page.inner_text('.result-grid'))
 # Learning mode, hints and immediate marking.
 page.goto(URL);page.locator('#math').click();page.select_option('#pick','מספר חסר');page.locator('#start').click()
 page.locator('#check').click();test('empty answer prompt','כתבי מספר' in page.inner_text('#status'))
 page.locator('#hint').click();test('hint visible',page.locator('.hint').count()==1)
 q=page.evaluate('STAGE_A_TEST.getSession().qs[0]');page.fill('#num',str(q['answer']));page.locator('#check').click();test('learning immediate correct',page.locator('.feedback.good').count()==1)
 page.fill('#num','999');test('editing clears feedback',page.locator('.feedback').count()==0)
 page.locator('#check').click();test('learning immediate wrong',page.locator('.feedback.bad').count()==1)
 page.fill('#num','1.5');page.locator('#next').click();test('decimal rejected',page.locator('#input-error').inner_text()!='')
 # All mathematics correct via typed answers, testing full 25 and navigation.
 page.goto(URL);page.locator('#test').click();page.locator('#math').click();page.select_option('#count','25');page.locator('#start').click()
 for i in range(25):
  q=page.evaluate('STAGE_A_TEST.getSession().qs[STAGE_A_TEST.getSession().index]')
  page.fill('#num',str(q['answer']));page.locator('#next').click()
 page.locator('#finish').click();test('math full result 25/25','25 מתוך 25' in page.inner_text('.result-grid'))
 # Timer and unanswered finish; expires with currently typed value saved.
 page.goto(URL);page.locator('#test').click();page.locator('#math').click();page.check('#use-time');page.fill('#minutes','4');page.locator('#start').click();test('invalid duration rejected',page.locator('#setup-error').inner_text()!='');page.fill('#minutes','5');page.locator('#start').click();q=page.evaluate('STAGE_A_TEST.getSession().qs[0]');page.fill('#num',str(q['answer']));page.evaluate('STAGE_A_TEST.getSession().seconds=1');page.wait_for_timeout(1150);test('timer expires','זמן האימון הסתיים' in page.inner_text('h1'));test('timer saves current typed answer','1 מתוך 5' in page.inner_text('.result-grid'))
 for width in [320,390,1280]:
  page.set_viewport_size({'width':width,'height':844 if width<1000 else 900});page.goto(URL);fits(page,f'home {width}');shot(page,f'home-{width}')
  page.select_option('#pick','p5');page.locator('#start').click();fits(page,f'reading {width}');shot(page,f'reading-{width}')
  page.locator('[data-option="0"]').click();page.locator('#check').click();fits(page,f'feedback {width}');shot(page,f'feedback-{width}')
  page.goto(URL);page.locator('#math').click();page.select_option('#pick','חידת סמלים');page.locator('#start').click();fits(page,f'math {width}');shot(page,f'math-{width}')
  page.goto(URL);page.locator('#print-menu').click();page.locator('#make-print').click();fits(page,f'print screen {width}');shot(page,f'print-{width}')
  if width==1280:
   page.emulate_media(media='print');page.pdf(path=str(OUT/'stage-a-practice.pdf'),format='A4',print_background=False);page.emulate_media(media='screen')
 test('no browser errors',not errors)
 b.close()
(OUT/'test-results.json').write_text(json.dumps({'checks':len(logs),'passed':True,'errors':errors,'tests':logs},ensure_ascii=False,indent=2))
print('PASS',len(logs),'checks; screenshots and PDF:',OUT)
