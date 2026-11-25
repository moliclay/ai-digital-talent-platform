(async () => {
  const button = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '出卷');
  if (!button) return 'no-button';
  button.click();
  await new Promise((r) => setTimeout(r, 600));
  return JSON.stringify({ audience: document.body.innerText.includes('受众'), bank: document.body.innerText.includes('算法基础题库'), text: document.body.innerText.slice(-420) });
})()
