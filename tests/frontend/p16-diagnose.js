(async () => {
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const pick = async (selector, label) => {
    const box = document.querySelector(selector);
    if (!box) return false;
    box.click();
    await wait(200);
    const option = [...document.querySelectorAll('[role="option"]')].find((el) => el.textContent.trim() === label);
    if (!option) return false;
    option.click();
    await wait(400);
    return true;
  };
  await pick('#diagnose-candidate', '陈宇');
  const btn = [...document.querySelectorAll('button')].find((el) => el.textContent.trim() === '开始诊断');
  if (btn) btn.click();
  await wait(1600);
  return document.body.innerText.includes('业务理解') ? 'diagnosed-chenyu' : 'failed';
})()
