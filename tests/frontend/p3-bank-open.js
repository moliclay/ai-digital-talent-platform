(async () => {
  const button = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '新建题库');
  if (!button) return 'no-button';
  button.click();
  await new Promise((r) => setTimeout(r, 600));
  return JSON.stringify({ audience: document.body.innerText.includes('受众'), text: document.body.innerText.slice(-420) });
})()
