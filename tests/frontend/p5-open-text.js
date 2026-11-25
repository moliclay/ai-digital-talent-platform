(async () => {
  const labels = ['查看画像', '绑定测评', '导入题库'];
  const button = [...document.querySelectorAll('button')].find((el) => labels.includes((el.innerText || '').trim()));
  if (!button) return 'no-trigger';
  button.click();
  await new Promise((r) => setTimeout(r, 700));
  return JSON.stringify({ label: (button.innerText || '').trim(), modal: Boolean(document.querySelector('[role="dialog"]')) });
})()
