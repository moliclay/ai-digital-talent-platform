(async () => {
  const wait = async (check) => { for (let i = 0; i < 80; i++) { if (check()) return; await new Promise(r => setTimeout(r, 100)); } throw new Error('等待聊天状态超时'); };
  const click = (label) => { const button = [...document.querySelectorAll('button')].find(b => b.innerText.trim() === label); if (!button) throw new Error('找不到按钮 ' + label); button.click(); };
  await wait(() => document.body.innerText.includes('今天想了解什么'));
  click('查找有 Python 技能的人才');
  await wait(() => document.body.innerText.includes('合成人才 A · #1'));
  await wait(() => [...document.querySelectorAll('button')].some(b => b.innerText.trim() === '新建对话' && !b.disabled));
  click('新建对话');
  await wait(() => document.body.innerText.includes('今天想了解什么'));
  click('查找有 Python 技能的人才');
  await wait(() => document.body.innerText.includes('合成人才 A · #1'));
  await wait(() => [...document.querySelectorAll('button')].some(b => b.innerText.trim() === '新建对话' && !b.disabled));
  click('新建对话');
  const button = [...document.querySelectorAll('button')].find(b => b.title === '测试会话');
  if (!button) throw new Error('未展示历史会话');
  button.click();
  await wait(() => document.body.innerText.includes('合成测试回答'));
  return { passed: true, path: location.pathname, overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth };
})()
