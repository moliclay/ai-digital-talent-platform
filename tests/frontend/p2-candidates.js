(async () => {
  const tab = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '岗位召回');
  if (!tab) return 'no-tab';
  tab.click();
  await new Promise((r) => setTimeout(r, 2400));
  return JSON.stringify({ rows: document.querySelectorAll('tbody tr').length, text: document.body.innerText.includes('程磊') });
})()
