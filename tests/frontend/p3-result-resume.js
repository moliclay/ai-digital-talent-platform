(async () => {
  const link = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '查看候选人简历');
  if (!link) return 'no-link';
  link.click();
  await new Promise((r) => setTimeout(r, 1100));
  return JSON.stringify({ path: location.pathname + location.search, modal: document.body.innerText.includes('李娜 · 简历') });
})()
