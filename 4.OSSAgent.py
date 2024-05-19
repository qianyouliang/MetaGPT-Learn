import asyncio
import os
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, Optional, List
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

# 修复 SubscriptionRunner 未完全定义的问题
from metagpt.environment import Environment as _  # noqa: F401
from dotenv import load_dotenv 
load_dotenv() # 加载我们配置在.env文件中的环境变量

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
        # 异步订阅方法
        loop = asyncio.get_running_loop()

        async def _start_role():
            async for msg in trigger:
                resp = await role.run(msg)
                await callback(resp)

        self.tasks[role] = loop.create_task(_start_role(), name=f"Subscription-{role}")

    async def unsubscribe(self, role: Role):
        """取消订阅角色并取消关联的任务"""
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
    async def run(self, url: str = "https://github.com/trending/python?since=weekly"):
        # 定义一个异步方法run，用于执行爬虫动作
        # URL默认为GitHub上按星标排名的Python项目周榜单

        async with aiohttp.ClientSession() as client:
            # 使用aiohttp创建一个会话对象client
            async with client.get(url) as response:
                # 使用client对象发送GET请求，并使用代理配置
                response.raise_for_status()
                # 如果响应状态码不是200，则raise_for_status()会抛出HTTPError异常
                html = await response.text()
                # 获取响应的HTML文本

        soup = BeautifulSoup(html, 'html.parser')
        # 使用BeautifulSoup解析HTML文本，生成一个BeautifulSoup对象

        repositories = []
        # 创建一个空列表，用于存储爬取到的仓库信息
        g = Github(os.getenv("GITHUB_ACCESS_TOKEN"))
        # 使用您的 GitHub 访问令牌创建一个 Github 对象
        for article in soup.select('article.Box-row'):
            # 使用 CSS 选择器选择所有类名为 Box-row 的 article 标签
            repo_info = {}
            # 创建一个空字典，用于存储单个仓库的信息
            repo_info['name'] = article.select_one('h2 a').text.strip().replace('\n', '').replace(' ', '')
            # 获取仓库名称，使用 CSS 选择器选择 h2 标签下的 a 标签，并提取其文本内容
            print(repo_info['name'])
            repo_info['url'] = "https://github.com"+article.select_one('h2 a')['href'].strip()
            # 获取仓库 URL，使用 CSS 选择器选择 h2 标签下的 a 标签，并提取其 href 属性值,并拼接成完整的 GitHub 仓库链接

            # 获取 README.md 文件
            try:
                # 尝试获取仓库的 README.md 文件
                repo = g.get_repo(repo_info['name'])
                contents = repo.get_contents("README.md", ref="main")
                repo_info['readme'] = contents.decoded_content.decode()
                print(repo_info['readme'])
            except Exception as e:
                # 如果仓库没有 README.md 文件或发生其他错误，则打印错误信息并跳过该仓库
                print(f"Error getting README.md file for {repo_info['name'] }: {e}")
                repo_info['readme'] = None
                continue

            # Description
            description_element = article.select_one('p')
            repo_info['description'] = description_element.text.strip() if description_element else None
            # 获取仓库描述信息，如果不存在则设置为None

            # Language
            language_element = article.select_one('span[itemprop="programmingLanguage"]')
            repo_info['language'] = language_element.text.strip() if language_element else None
            # 获取仓库使用的编程语言，如果不存在则设置为None

            # Stars and Forks
            stars_element = article.select('a.Link--muted')[0]
            forks_element = article.select('a.Link--muted')[1]
            repo_info['stars'] = stars_element.text.strip()
            repo_info['forks'] = forks_element.text.strip()
            # 获取仓库的星标数和分支数

            # week's Stars
            today_stars_element = article.select_one('span.d-inline-block.float-sm-right')
            repo_info['week_stars'] = today_stars_element.text.strip() if today_stars_element else None
            # 获取仓库在本周新增的星标数，如果不存在则设置为None

            if repo_info.get("readme") != None:
                repositories.append(repo_info)
                # 将仓库信息添加到列表中

        return json.dumps(repositories[:2])# 使用json.dumps将字典转换为JSON字符串，并存储到字符串中 返回爬取到的仓库信息列表

# Actions 的实现
class AnalysisOSSRepository(Action):
    def prompt_format(self,repo_info):
        question = """# 需求
您是一名 GitHub 仓库分析师，旨在为用户提供有见地的、个性化的仓库分析。根据上下文，填写以下缺失的信息，生成吸引人并有信息量的标题，确保用户发现与其兴趣相符的仓库。

关于仓库的标题
仓库分析：深入探索 xxx项目的特点和优势！基于基本内容，如网页链接，了解其背后的作用，技术栈，实现思路，部署方式等信息。
---
格式示例

```
# 项目名称

## 项目地址
xxx
## 仓库介绍
xxx 是一个用于 xxx 的开源项目。它使用 xxx 技术栈实现，采用 xxx 的实现思路。

## 特点和优势
- 特点1
- 特点2

## 部署和使用
可以通过 <部署方式，如Docker,本地部署，云服务器> 的方式部署和使用该项目。详细信息可以参考以下链接：
- 项目文档：[name](url)
- 演示页面：[name](url)
- 执行代码：
> pip install ...
```

---
当前已有信息如下:
项目名称:{repository_name}
项目地址:{repository_URL}
项目Star:{repository_star}
项目Fork:{repository_fork}
项目语言：{repository_language}
项目readme:{repository_readme}
""".format(repository_name=repo_info["name"], repository_URL=repo_info["url"], repository_star=repo_info["stars"], repository_fork=repo_info["forks"], repository_language=repo_info["language"], repository_readme=repo_info["readme"])
        return question

    async def run(self, repo_info_list: Any):
        repo_summary_list = []
        for repo_info in json.loads(repo_info_list):
            repository_info = self.prompt_format(repo_info)
            summary = await self._aask(repository_info)
            repo_summary_list.append(summary)
        return repo_summary_list

# 角色设计
class OssWatcher(Role):
    def __init__(self):
        super().__init__(
            name="cheems",
            profile="OssWatcher",
            goal="根据我提供给你的资料生成一个有见地的 GitHub 仓库 分析报告。",
            constraints="仅基于提供的 GitHub 仓库 数据进行分析。",
        )
        self.set_actions([CrawlAction(), AnalysisOSSRepository()])
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
class GithubTrendingCronTrigger:
    def __init__(self, spec: str, tz: Optional[BaseTzInfo] = None, url: str = "https://github.com/trending/python?since=weekly") -> None:
        self.crontab = crontab(spec, tz=tz)
        self.url = url

    def __aiter__(self):
        return self

    async def __anext__(self):
        await self.crontab.next()
        return Message(content=self.url)

# discord 回调
async def discord_callback(msg_list: List):
    intents = discord.Intents.default()
    intents.message_content = True
    # client = discord.Client(intents=intents, proxy= os.getenv("GLOBAL_PROXYGLOBAL_PROXY")) # 需要代理
    client = discord.Client(intents=intents) # 无需代理
    token = os.getenv("DISCORD_TOKEN")
    channel_id = int(os.getenv("DISCORD_CHANNEL_ID"))
    async with client:
        await client.login(token)
        channel = await client.fetch_channel(channel_id)
        for repo in msg_list:
            lines = []
            for line in repo.splitlines():
                if line.startswith(("# ", "## ", "### ")):
                    if lines:
                        await channel.send("\n".join(lines))
                        lines = []
                lines.append(line)

            if lines:
                await channel.send("\n".join(lines))


# 运行入口
async def main(spec: str = "* * * * *", discord: bool = True, wxpusher: bool = True):
    callbacks = []
    if discord:
        callbacks.append(discord_callback)

    if not callbacks:
        async def _print(msg: Message):
            print(msg.content)

        callbacks.append(_print)

    async def callback(msg):
        await asyncio.gather(*(call(msg) for call in callbacks))

    runner = SubscriptionRunner()
    await runner.subscribe(OssWatcher(), GithubTrendingCronTrigger(spec), callback) # 正式版本
    await runner.run()

if __name__ == "__main__":
    import fire
    fire.Fire(main) # 使用 fire 库将 main 函数转换为命令行接口的入口点