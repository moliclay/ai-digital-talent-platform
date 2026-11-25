(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const setValue = (selector, value) => {
    const el = document.querySelector(selector);
    if (!el) return false;
    const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
    setter.call(el, value);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    return true;
  };
  const record = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '记录进度');
  if (!record) return JSON.stringify({ step: 'no-record', text: document.body.innerText.slice(-400) });
  record.click();
  await sleep(500);
  setValue('#my-task-minutes', '600');
  setValue('#my-task-progress', '100');
  await sleep(200);
  const save = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '保存');
  if (!save) return 'no-save';
  save.click();
  await sleep(1800);
  const complete = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '完成学习' && !el.disabled);
  if (!complete) return JSON.stringify({ step: 'complete-disabled', text: document.body.innerText.slice(0, 650) });
  complete.click();
  await sleep(1800);
  return JSON.stringify({ done: document.body.innerText.includes('已完成'), text: document.body.innerText.slice(0, 650) });
})()
