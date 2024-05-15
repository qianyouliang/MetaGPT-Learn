import re
import asyncio
from metagpt.actions import Action
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger

class CodeWrite(Action):
    PROMPT_TEMPLATE: str = """
    根据以下需求，编写一个能够实现{requirements}的Python函数，并提供两个可运行的测试用例。
    返回的格式为：```python\n你的代码\n```，请不要包含其他的文本。
    ```python
    # your code here
    ```
    """

    name: str = "CodeWriter"

    async def run(self, requirements: str):
        prompt = self.PROMPT_TEMPLATE.format(instruction=requirements)
        rsp = await self._aask(prompt)
        code_text = CodeWrite.parse_code(rsp)
        return code_text

    @staticmethod
    def parse_code(rsp): # 从模型生成中字符串匹配提取生成的代码
        pattern = r'```python(.*?)```'  # 使用非贪婪匹配
        match = re.search(pattern, rsp, re.DOTALL)
        code_text = match.group(1) if match else rsp
        return code_text

class CodeWriter(Role):
    """
    CodeWriter 角色类，继承自 Role 基类
    """

    name: str = "Cheems"  # 角色昵称
    profile: str = "CodeWriter"  # 角色人设

    def __init__(self, **kwargs):
        """
        初始化 CodeWriter 角色
        """
        super().__init__(**kwargs)  # 调用基类构造函数
        self._init_action(CodeWrite)  # 为角色配备 CodeWrite 动作

    async def _act(self) -> Message:
        """
        定义角色行动逻辑
        """
        logger.info(f"{self._setting}: ready to {self.rc.todo}")  # 记录日志
        todo = self.rc.todo  # 获取待执行的动作 (CodeWriter)

        msg = self.get_memories(k=1)[0]  # 获取最近一条记忆 (用户输入)

        code_text = await todo.run(msg.content)  # 执行 CodeWrite 动作，获取生成的代码
        msg = Message(content=code_text, role=self.profile, cause_by=type(todo))  # 构造 Message 对象

        return msg  # 返回生成的 Message

async def main():
    msg = "如何用python获取最新的股票统计数据？"
    role = CodeWriter() # 实例化CodeWrite
    logger.info(msg) # 记录日志信息
    result = await role.run(msg) # 得到运行结果
    logger.info(result) # 记录运行结果

asyncio.run(main()) # 异步运行main函数 # 正常python文件使用