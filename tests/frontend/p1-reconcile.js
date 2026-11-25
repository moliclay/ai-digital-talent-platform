(async () => {
  const open = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '查看分组');
  if (!open) return 'missing-open';
  open.click();
  await new Promise((resolve) => setTimeout(resolve, 400));
  const recalc = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '重新计算身份');
  if (!recalc) return 'missing-recalc';
  recalc.click();
  await new Promise((resolve) => setTimeout(resolve, 400));
  const confirm = [...document.querySelectorAll('button')].find((el) => (el.innerText || '').trim() === '重新计算');
  if (!confirm) return 'missing-confirm';
  confirm.click();
  await new Promise((resolve) => setTimeout(resolve, 1800));
  return document.body.innerText.includes('已重算');
})()
