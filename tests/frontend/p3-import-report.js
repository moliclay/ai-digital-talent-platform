(async () => {
  await new Promise((r) => setTimeout(r, 12000));
  return JSON.stringify({ summary: document.body.innerText.includes('识别'), draft: document.body.innerText.includes('题目草稿'), warnings: document.body.innerText.includes('解析提示'), busy: document.body.innerText.includes('正在解析'), text: document.body.innerText.slice(-600) });
})()
