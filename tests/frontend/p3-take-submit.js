(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const start = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '开始答题');
  if (start) { start.click(); await sleep(1000); }

  const radios = [...document.querySelectorAll('input[type="radio"]')];
  const seen = new Set();
  for (const radio of radios) {
    if (!seen.has(radio.name)) { seen.add(radio.name); radio.click(); }
  }
  const checks = [...document.querySelectorAll('input[type="checkbox"]')];
  for (const check of checks.slice(0, 3)) check.click();
  const textarea = document.querySelector('textarea');
  if (textarea) {
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
    setter.call(textarea, 'Q/K/V、缩放点积、多头注意力');
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
  }
  await sleep(300);
  const submit = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '交卷');
  if (!submit) return JSON.stringify({ step: 'no-submit', path: location.pathname + location.search });
  submit.click();
  await sleep(500);
  const confirm = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '确定交卷');
  if (confirm) confirm.click();
  await sleep(4500);
  return JSON.stringify({ path: location.pathname + location.search, h1: document.querySelector('h1')?.textContent, text: document.body.innerText.slice(0, 500) });
})()
