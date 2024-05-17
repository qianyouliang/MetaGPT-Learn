import asyncio
from metagpt.actions.write_tutorial import WriteDirectory, WriteContent
from metagpt.logs import logger
from metagpt.roles.role import Role
from metagpt.schema import Message
from metagpt.actions import Action
from metagpt.prompts.tutorial_assistant import DIRECTORY_PROMPT, CONTENT_PROMPT
from metagpt.utils.common import OutputParser

# 定义 Action 类，继承自 metagpt.actions.Action
class PrintAction(Action):
    def __init__(self, ID, name, content, day, period):
        super().__init__()
        self.ID = ID
        self.name = name
        self.content = content
        self.day = day
        self.period = period
        self.state = 0  # 初始化状态为 0，未执行

    async def run(self):
        try:
            self.content = await self._aask(f"这是我们的聊天历史:{self.content}，当前时间是第{self.day}天，{self.period}，请你继续与我以一个心理医生角度交谈，内容要符合时间，而不是一个AI，,回复要推动事情发展前进，而不是只考虑一个话题；现在针对我的话进行回复即可")
            self.state = 2  # 执行成功，状态更新为 2
        except Exception as e:
            print(e)
            self.state = 1  # 执行失败，状态更新为 1
        return self.content  # 确保返回一个字符串

class PrintAgent(Role):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.actions = []  # 初始化动作列表
        self.action_id = 0  # 初始化动作 ID
        self.day = 1  # 从第1天开始
        self.periods = ["早晨", "下午", "晚上"]
        self.profile = "cheems"

        # 初始化前三个固定的 PrintAction
        self.add_initial_actions()

    def add_initial_actions(self):
        initial_contents = [
            '你叫什么名字？',
            'Cheems,我感到很累？我整天996工作，但是我别无选择，医生，我该怎么办',
            '讲讲你的故事，Cheems，我愿意倾听..'
        ]
        for index, content in enumerate(initial_contents):
            self.action_id += 1
            action = PrintAction(self.action_id, f"打印{self.action_id}", content, self.day, self.periods[index])
            self.add_action(action)

    def add_action(self, action):
        self.actions.append(action)  # 添加动作到动作列表

    async def run_actions(self):
        for action in self.actions:
            todo = self.rc.todo  # 按照排列顺序获取待执行的动作
            logger.info(f"{self._setting}: 准备动作{action.ID},今天是第{action.day}天, {action.period}")  # 记录日志
            msg = await action.run()  # 顺序执行动作
            msg = Message(content=msg or "", role=self.profile, cause_by=type(todo))
            self.rc.memory.add(msg)  # 将执行结果添加到记忆
        self.day += 1

        self.actions = []  # 清空动作列表

    def generate_actions(self):
        # 生成三个新的动作，ID 递增
        for i in range(3):
            self.action_id += 1
            msg = self.get_memories(k=1)[0]  # 获取最相似的1条记忆
            action = PrintAction(self.action_id, f"打印{self.action_id}", msg, self.day, self.periods[i])
            self.add_action(action)

    async def _act(self) -> Message:
        while True:
            if not self.actions:  # 如果动作列表为空
                self.generate_actions()  # 生成新的动作
            await self.run_actions()  # 执行动作
            await asyncio.sleep(1)  # 添加一个短暂的休眠，以防止无限循环导致过高的 CPU 占用
        return Message(content="动作执行完毕", role=self.profile)

# 异步主函数
async def main():
    agent = PrintAgent()  # 创建 医生 实例
    await agent._act()  # 执行动作

# 运行异步主函数
asyncio.run(main())