(async () => {
  const button = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '员工');
  if (!button) return 'no-button';
  button.click();
  await new Promise((r) => setTimeout(r, 1200));
  return JSON.stringify({ empty: document.body.innerText.includes('还没有题库'), create: document.body.innerText.includes('新建题库'), text: document.body.innerText.slice(0, 500) });
})()
