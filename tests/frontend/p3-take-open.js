(async () => {
  const button = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '开始答题');
  if (!button) return 'no-button';
  button.click();
  await new Promise((r) => setTimeout(r, 1100));
  return JSON.stringify({ path: location.pathname + location.search, title: document.querySelector('h1')?.textContent, text: document.body.innerText.slice(0, 600) });
})()
