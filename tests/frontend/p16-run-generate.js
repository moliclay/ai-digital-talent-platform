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
  const click = (label, last = false) => {
    const buttons = [...document.querySelectorAll('button')].filter((el) => el.textContent.trim() === label);
    const button = last ? buttons[buttons.length - 1] : buttons[0];
    if (button) button.click();
    return Boolean(button);
  };
  const setInput = (selector, value) => {
    const input = document.querySelector(selector);
    if (!input) return false;
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(input, value);
    input.dispatchEvent(new Event('input', { bubbles: true }));
    return true;
  };
  if (!(await pick('#diagnose-job', 'AI 产品经理'))) return 'no-job';
  click('开始诊断');
  await wait(1500);
  click('生成培养计划');
  await wait(600);
  setInput('#plan-weeks', '4');
  setInput('#plan-mentor', '王工');
  await wait(200);
  click('生成培养计划', true);
  await wait(2600);
  return document.body.innerText.includes('培养方案') ? 'generated' : 'failed';
})()
