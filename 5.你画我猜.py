import re
import fire
from metagpt.actions import Action, UserRequirement
from metagpt.logs import logger
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.team import Team
from dotenv import load_dotenv
from typing import ClassVar

load_dotenv()

# 描述Action
class DescribeItem(Action):
    PROMPT_TEMPLATE: str = """
    请根据以下物体词汇生成描述文本：
    可以对物体词汇侧面描写，但是不能直接说明其名称，你的生成内容是让别人猜测的；
    例如： "苹果": "这是一种红色或绿色的水果，圆形，味道甜或酸。"
    "桌子": "这是一个家具，有四条腿，用来放置物品。",
    当前如下：
    词汇：{word}
    """
    name: str = "DescribeItem"

    async def run(self, word):
        prompt = self.PROMPT_TEMPLATE.format(word=word)
        res = await self._aask(prompt)
        return res

# 猜测Action
class GuessItem(Action):
    PROMPT_TEMPLATE: str = """
    根据以下描述文本进行猜测物体名称：
    描述：{description}
    例如：描述为："这是一种红色或绿色的水果，圆形，味道甜或酸。"，你需要猜测为: "苹果",
    你的输出格式如下，猜测结果用方括号扩住：
    [苹果]
    """
    name: str = "Guess"

    async def run(self, description):
        prompt = self.PROMPT_TEMPLATE.format(description=description)
        result = await self._aask(prompt)
        return self.parse_item(result)
    
    @staticmethod
    def parse_item(rsp):
        pattern = r'\[(.*?)\]'
        match = re.search(pattern, rsp, re.DOTALL)
        item = match.group(1) if match else rsp
        return item

class DescriberAgent(Role):
    name: str = "Describer"
    profile: str = "负责生成物体描述文本的描述者"
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._watch([UserRequirement,GuessItem])
        self.set_actions([DescribeItem])

    async def _act(self) -> Message:
        """
        描述者动作：根据猜测者的回答修改描述。
        """
        logger.info(f"{self._setting}: ready to {self.rc.todo}")
        todo = self.rc.todo

        msg = self.get_memories()  # 获取所有对话记忆
        # logger.info(msg)
        prompt = "这是猜测者的返回：{msg},如果这不是正确答案，请修改描述"
        describe = await DescribeItem().run(prompt)
        logger.info(f'DescriberAgent : {describe}')
        msg = Message(content=describe, role=self.profile, cause_by=type(todo))

        return msg

class GuesserAgent(Role):
    name: str = "Guesser"
    profile: str = "负责猜测物体名称的猜测者"
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._watch([DescribeItem])
        self.set_actions([GuessItem])
    async def _act(self) -> Message:
        """
        猜测者动作：根据描述者的描述修改猜测结果。
        """
        logger.info(f"{self._setting}: ready to {self.rc.todo}")
        todo = self.rc.todo

        msg = self.get_memories()  # 获取所有对话记忆
        # logger.info(msg)
        prompt = "这是描述者的返回：{msg},如何这不是正确答案，请修改结果重新回答"
        guess = await GuessItem().run(msg)
        logger.info(f'GuesserAgent : {guess}')
        msg = Message(content=guess, role=self.profile, cause_by=type(todo))

        return msg

async def main(word: str = "猫", idea: str = "鸡你太美", investment: float = 3.0, add_human: bool = False, n_round=5):
    logger.info(idea)
    team = Team()
    team.hire([DescriberAgent(), GuesserAgent()])
    team.invest(investment=investment)
    team.run_project(idea) # 初始化项目

    await team.run(n_round=n_round) # 开始循环
    

if __name__ == "__main__":
    fire.Fire(main)