(async () => {
  const button = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '导入题库');
  if (!button) return 'no-button';
  button.click();
  await new Promise((r) => setTimeout(r, 700));
  return JSON.stringify({ dialog: document.body.innerText.includes('上传后只生成草稿') });
})()
