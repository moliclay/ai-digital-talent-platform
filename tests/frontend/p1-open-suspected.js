(async () => {
  const button = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '查看分组');
  if (!button) return 'missing';
  button.click();
  await new Promise((resolve) => setTimeout(resolve, 600));
  return 'opened';
})()
