from datetime import datetime
from typing import Dict
import asyncio
from metagpt.actions.write_tutorial import WriteDirectory, WriteContent
from metagpt.const import TUTORIAL_PATH
from metagpt.logs import logger
from metagpt.roles.role import Role, RoleReactMode
from metagpt.schema import Message
from metagpt.utils.file import File

from typing import Dict

from metagpt.actions import Action
from metagpt.prompts.tutorial_assistant import DIRECTORY_PROMPT, CONTENT_PROMPT
from metagpt.utils.common import OutputParser

# 定义 Action 类，继承自 metagpt.actions.Action
class PrintAction(Action):
    def __init__(self, ID, name, content):
        super().__init__()
        self.ID = ID
        self.name = name
        self.content = content
        self.state = 0  # 初始化状态为 0，未执行

    async def run(self):
        try:
            self.content = await self._aask(f"有什么想聊的吗，这是我之前说的话:{self.content}，你补充下一句")
            print(self.content)  # 执行动作，打印内容
            self.state = 2  # 执行成功，状态更新为 2
        except Exception as e:
            print(e)
            self.state = 1  # 执行失败，状态更新为 1

# 定义 Print Agent 类，继承自 metagpt.roles.Role
class PrintAgent(Role):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.actions = []  # 初始化动作列表
        self.action_id = 0  # 初始化动作 ID

    def add_action(self, action):
        self.actions.append(action)  # 添加动作到动作列表

    async def run_actions(self):
        for action in self.actions:
            await action.run()  # 顺序执行动作
            self.memory.add(action)  # 将执行结果添加到记忆
        self.actions = []  # 清空动作列表

    def generate_actions(self):
        # 生成三个新的动作，ID 递增
        for i in range(3):
            self.action_id += 1
            action = PrintAction(self.action_id, f"打印{self.action_id}", f"这是动作{self.action_id}")
            self.add_action(action)

    async def _act(self) -> Message:
        if not self.actions:  # 如果动作列表为空
            self.generate_actions()  # 生成新的动作
        await self.run_actions()  # 执行动作
        return Message(content="动作执行完毕", role=self.profile)

# 异步主函数
async def main():
    agent = PrintAgent()  # 创建 PrintAgent 实例
    await agent._act()  # 执行动作

# 运行异步主函数
asyncio.run(main())
