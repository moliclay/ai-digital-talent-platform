(async () => {
  const button = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '程磊');
  if (!button) return 'missing';
  button.click();
  await new Promise((r) => setTimeout(r, 700));
  return JSON.stringify({ search: location.search, modal: document.body.innerText.includes('程磊 · 简历') });
})()
