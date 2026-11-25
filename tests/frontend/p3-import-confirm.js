(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  await sleep(9000);
  const confirm = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '确认导入');
  if (!confirm) return JSON.stringify({ step: 'no-confirm', text: document.body.innerText.slice(-400) });
  confirm.click();
  await sleep(2200);
  return JSON.stringify({ done: document.body.innerText.includes('已导入'), text: document.body.innerText.slice(-500) });
})()
