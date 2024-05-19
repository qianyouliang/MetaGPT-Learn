import asyncio
import os
import smtplib
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, Optional, List
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from github import Github
import aiohttp
import discord
from aiocron import crontab
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from pytz import BaseTzInfo
import json

from metagpt.actions.action import Action
from metagpt.logs import logger
from metagpt.roles import Role
from metagpt.schema import Message

# 加载环境变量
from dotenv import load_dotenv 
load_dotenv()

# 订阅模块
class SubscriptionRunner(BaseModel):
    tasks: Dict[Role, asyncio.Task] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True

    async def subscribe(
        self,
        role: Role,
        trigger: AsyncGenerator[Message, None],
        callback: Callable[[Message], Awaitable[None]],
    ):
        loop = asyncio.get_running_loop()

        async def _start_role():
            async for msg in trigger:
                resp = await role.run(msg)
                await callback(resp)

        self.tasks[role] = loop.create_task(_start_role(), name=f"Subscription-{role}")

    async def unsubscribe(self, role: Role):
        task = self.tasks.pop(role)
        task.cancel()

    async def run(self, raise_exception: bool = True):
        while True:
            for role, task in self.tasks.items():
                if task.done():
                    if task.exception():
                        if raise_exception:
                            raise task.exception()
                        logger.opt(exception=task.exception()).error(
                            f"Task {task.get_name()} run error"
                        )
                    else:
                        logger.warning(
                            f"Task {task.get_name()} has completed. "
                            "If this is unexpected behavior, please check the trigger function."
                        )
                    self.tasks.pop(role)
                    break
            else:
                await asyncio.sleep(1)

# 定义一个爬虫动作类，继承自Action类
class CrawlAction(Action):
    async def run(self, url: str = "https://huggingface.co/papers"):
        async with aiohttp.ClientSession() as client:
            papers = await self._fetch_papers(url, client)
            return json.dumps(papers[:5])  # 获取前5篇Paper信息

    async def _fetch_papers(self, url: str, client: aiohttp.ClientSession):
        async with client.get(url) as response:
            response.raise_for_status()
            html = await response.text()

        soup = BeautifulSoup(html, 'html.parser')
        papers = []
        
        # 只爬取前5页
        for article in soup.select('h3 > a[href^="/papers/"]')[:5]:
            paper_info = {}
            paper_info['title'] = article.text.strip()
            print(article.text.strip())
            paper_info['url'] = "https://huggingface.co" + article['href'].strip()
            paper_html = await self._fetch_paper_detail(paper_info['url'], client)
            paper_soup = BeautifulSoup(paper_html, 'html.parser')
            paper_info['abstract'] = paper_soup.find("section").get_text(separator=' ', strip=True).strip()
            papers.append(paper_info)

        return papers

    async def _fetch_paper_detail(self, url: str, client: aiohttp.ClientSession) -> str:
        async with client.get(url) as response:
            response.raise_for_status()
            return await response.text()

# Actions 的实现
class AnalysisPaper(Action):
    def prompt_format(self, paper_info):
        question = """# 需求
您是一名学术论文分析师，旨在为用户提供有见地的、个性化的论文分析。根据上下文，填写以下缺失的信息，生成吸引人并有信息量的标题，确保用户发现与其兴趣相符的论文。

关于论文的标题
论文分析：深入探索 xxx论文的特点和贡献！基于基本内容，如网页链接，了解其背后的研究背景，研究方法，实验结果等信息。
---
格式示例
# 论文标题

## 论文链接

xxx

## 论文摘要

xxx

## 研究背景

xxx

## 研究方法

xxx

## 实验结果

xxx

## 结论

xxx
---
当前已有信息如下:
论文标题:{paper_title}
论文链接:{paper_URL}
论文摘要:{paper_abstract}
""".format(paper_title=paper_info["title"], paper_URL=paper_info["url"], paper_abstract=paper_info["abstract"])
        return question

    async def run(self, paper_info_list: Any):
        paper_summary_list = []
        for paper_info in json.loads(paper_info_list):
            paper_info_str = self.prompt_format(paper_info)
            summary = await self._aask(paper_info_str)
            paper_summary_list.append(summary)
        return paper_summary_list

# 角色设计
class PaperWatcher(Role):
    def __init__(self):
        super().__init__(
            name="cheems",
            profile="PaperWatcher",
            goal="根据我提供给你的资料生成一个有见地的学术论文分析报告。",
            constraints="仅基于提供的论文数据进行分析。",
        )
        self.set_actions([CrawlAction(), AnalysisPaper()])
        self._set_react_mode(react_mode="by_order")

    async def _act(self) -> Message:
        logger.info(f"{self._setting}: ready to {self.rc.todo}")
        todo = self.rc.todo

        msg = self.get_memories(k=1)[0]
        result = await todo.run(msg.content)

        new_msg = Message(content=str(result), role=self.profile, cause_by=type(todo))
        self.rc.memory.add(new_msg)
        return result

# 定义一个基于aiocron的定时触发器类
class HuggingfacePapersCronTrigger:
    def __init__(self, spec: str, tz: Optional[BaseTzInfo] = None, url: str = "https://huggingface.co/papers") -> None:
        self.crontab = crontab(spec, tz=tz)
        self.url = url

    def __aiter__(self):
        return self

    async def __anext__(self):
        await self.crontab.next()
        return Message(content=self.url)

# 邮件回调
async def email_callback(paper_summary_list: List):
    gmail_user = os.getenv("QQ_EMAIL_USER")
    gmail_password = os.getenv("QQ_EMAIL_PASSWORD")
    to = os.getenv("QQ_EMAIL_TO")
    
    subject = "Huggingface Papers Weekly Digest"
    body = "\n\n".join(paper_summary_list)

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = gmail_user
    msg['To'] = to

    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP('smtp.qq.com', 587)
    server.starttls()
    server.login(gmail_user, gmail_password)
    server.send_message(msg)
    server.quit()
    print("send success!")

# 运行入口
async def main(spec: str = "* * * * *", email: bool = True):
    callbacks = []
    if email:
        callbacks.append(email_callback)

    if not callbacks:
        async def _print(msg: Message):
            print(msg.content)

        callbacks.append(_print)

    async def callback(msg):
        await asyncio.gather(*(call(msg) for call in callbacks))

    runner = SubscriptionRunner()
    await runner.subscribe(PaperWatcher(), HuggingfacePapersCronTrigger(spec), callback)
    await runner.run()

if __name__ == "__main__":
    import fire
    fire.Fire(main)