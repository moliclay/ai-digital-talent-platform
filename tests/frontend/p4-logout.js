(async () => {
  const button = document.querySelector('button[aria-label="退出登录"]');
  if (!button) return 'no-button';
  button.click();
  await new Promise((r) => setTimeout(r, 1200));
  return JSON.stringify({ path: location.pathname, login: document.body.innerText.includes('继续进入人才平台') });
})()
