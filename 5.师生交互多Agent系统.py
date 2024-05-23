import asyncio

from metagpt.actions import Action, UserRequirement
from metagpt.logs import logger
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.environment import Environment

from metagpt.const import MESSAGE_ROUTE_TO_ALL
# 加载环境变量
from dotenv import load_dotenv 
load_dotenv()

classroom = Environment()


class WriteAction(Action):
    """
    学生Agent的撰写作文Action。
    """
    name: str = "WriteEssay"

    PROMPT_TEMPLATE: str = """
    这里是历史对话记录：{msg}。
    请你根据用户提供的主题撰写一篇作文，只返回生成的作文内容，不包含其他文本。
    如果老师提供了关于作文的建议，请根据建议修改你的历史作文并返回。
    你的作文如下：
    """

    async def run(self, msg: str):
        """
        根据用户提供的主题撰写一篇作文，并在收到老师的修改建议后进行修改。
        """
        prompt = self.PROMPT_TEMPLATE.format(msg=msg)

        rsp = await self._aask(prompt)

        return rsp

class ReviewAction(Action):
    """
    老师Agent的审阅作文Action。
    """
    name: str = "ReviewEssay"

    PROMPT_TEMPLATE: str = """
    这里是历史对话记录：{msg}。
    你是一名老师，现在请检查学生创作的关于用户提供的主题的作文，并给出你的修改建议。你更喜欢逻辑清晰的结构和有趣的口吻。
    只返回你的修改建议，不要包含其他文本。
    你的修改建议如下：
    """

    async def run(self, msg: str):
        """
        审阅学生的作文，并给出修改建议。
        """
        prompt = self.PROMPT_TEMPLATE.format(msg=msg)

        rsp = await self._aask(prompt)

        return rsp


class Student(Role):
    """
    学生角色。
    """
    name: str = "cheems"
    profile: str = "Student"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([WriteAction])  # 设置学生的动作为撰写作文
        self._watch([UserRequirement, ReviewAction])  # 监听用户要求和老师的审阅动作

    async def _act(self) -> Message:
        """
        学生动作：根据用户要求撰写作文或根据老师的修改建议修改作文。
        """
        logger.info(f"{self._setting}: ready to {self.rc.todo}")
        todo = self.rc.todo

        msg = self.get_memories()  # 获取所有对话记忆
        # logger.info(msg)
        essay_text = await WriteAction().run(msg)
        logger.info(f'student : {essay_text}')
        msg = Message(content=essay_text, role=self.profile, cause_by=type(todo))

        return msg

class Teacher(Role):
    """
    老师角色。
    """
    name: str = "laobai"
    profile: str = "Teacher"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([ReviewAction])  # 设置老师的动作为审阅作文
        self._watch([WriteAction])  # 监听学生的撰写作文动作

    async def _act(self) -> Message:
        """
        老师动作：审阅学生的作文并给出修改建议。
        """
        logger.info(f"{self._setting}: ready to {self.rc.todo}")
        todo = self.rc.todo

        msg = self.get_memories()  # 获取所有对话记忆
        review_text = await ReviewAction().run(msg)
        logger.info(f'teacher : {review_text}')
        msg = Message(content=review_text, role=self.profile, cause_by=type(todo))

        return msg

class Student(Role):
    """
    学生角色。
    """
    name: str = "cheems"
    profile: str = "Student"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([WriteAction])  # 设置学生的动作为撰写作文
        self._watch([UserRequirement, ReviewAction])  # 监听用户要求和老师的审阅动作

    async def _act(self) -> Message:
        """
        学生动作：根据用户要求撰写作文或根据老师的修改建议修改作文。
        """
        logger.info(f"{self._setting}: ready to {self.rc.todo}")
        todo = self.rc.todo

        msg = self.get_memories()  # 获取所有对话记忆
        # logger.info(msg)
        essay_text = await WriteAction().run(msg)
        logger.info(f'student : {essay_text}')
        msg = Message(content=essay_text, role=self.profile, cause_by=type(todo))

        return msg

class Teacher(Role):
    """
    老师角色。
    """
    name: str = "laobai"
    profile: str = "Teacher"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([ReviewAction])  # 设置老师的动作为审阅作文
        self._watch([WriteAction])  # 监听学生的撰写作文动作

    async def _act(self) -> Message:
        """
        老师动作：审阅学生的作文并给出修改建议。
        """
        logger.info(f"{self._setting}: ready to {self.rc.todo}")
        todo = self.rc.todo

        msg = self.get_memories()  # 获取所有对话记忆
        review_text = await ReviewAction().run(msg)
        logger.info(f'teacher : {review_text}')
        msg = Message(content=review_text, role=self.profile, cause_by=type(todo))

        return msg

async def main(topic: str, n_round=5):
    """
    运行函数，用户输入一个主题，并将主题发布在环境中，然后运行环境。
    """
    classroom.add_roles([Student(), Teacher()])  # 向环境中添加学生和老师角色

    classroom.publish_message(
        Message(role="Human", content=topic, cause_by=UserRequirement,
                send_to='' or MESSAGE_ROUTE_TO_ALL),
        peekable=False,
    )
    # 发布一条消息，包含用户输入的主题，并将其发送给所有角色

    while n_round > 0:
        # self._save()
        n_round -= 1
        logger.debug(f"max {n_round=} left.")  # 输出剩余对话轮数

        await classroom.run()  # 运行环境
    return classroom.history  # 返回对话历史记录

asyncio.run(main(topic='关于道德和法律的限制范围'))  # 运行主函数，输入主题为 "道德和法律的限制范围"