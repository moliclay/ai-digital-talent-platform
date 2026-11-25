(async () => {
  const button = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '导入题库');
  if (!button) return 'no-trigger';
  button.click();
  await new Promise((r) => setTimeout(r, 700));
  return JSON.stringify({ modal: Boolean(document.querySelector('[role="dialog"]')), text: document.body.innerText.slice(-200) });
})()
