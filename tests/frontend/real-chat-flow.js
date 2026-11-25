(async () => {
  const wait = async (check) => { for (let i = 0; i < 600; i++) { if (check()) return; await new Promise(r => setTimeout(r, 100)); } throw new Error('等待超时: '+document.body.innerText.slice(-400)); };
  const click = (label) => { const b = [...document.querySelectorAll('button')].find(b => b.innerText.trim() === label); if (!b) throw new Error('找不到 '+label); b.click(); };
  await wait(() => !!document.querySelector('button[aria-label="填入演示账号 hr_zhao"]'));
  document.querySelector('button[aria-label="填入演示账号 hr_zhao"]').click();
  await wait(() => document.querySelector('input[name="username"]')?.value === "hr_zhao" && !!document.querySelector('input[name="password"]')?.value);
  document.querySelector('form').requestSubmit();
  await wait(() => location.pathname !== '/login' && !!localStorage.getItem('tl.token'));
  await wait(() => !!document.querySelector('a[href="/chat"]'));
  document.querySelector('a[href="/chat"]').click();
  await wait(() => document.body.innerText.includes('今天想了解什么'));
  click('查找有 Python 技能的人才');
  await wait(() => document.body.innerText.includes('业务来源') && [...document.querySelectorAll('button')].some(b=>b.innerText.trim()==='新建对话' && !b.disabled));
  const title = '查找有 Python 技能的人才';
  click('新建对话');
  await wait(() => document.body.innerText.includes('今天想了解什么'));
  const history = [...document.querySelectorAll('button')].find(b => b.title === title);
  if (!history) throw new Error('历史记录缺失');
  history.click();
  await wait(() => document.body.innerText.includes('业务来源'));
  await wait(() => [...document.querySelectorAll('button')].some(b=>b.innerText.trim()==='新建对话' && !b.disabled));
  click('新建对话');
  await wait(() => document.body.innerText.includes('今天想了解什么'));
  click('搜索有 RAG 项目经验的人才');
  await wait(() => [...document.querySelectorAll('button')].some(b=>b.innerText.trim()==='停止生成'));
  click('停止生成');
  await wait(() => document.body.innerText.includes('已停止') || document.body.innerText.includes('今天想了解什么'));
  return { passed: true, path: location.pathname, overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth };
})()
