import re
import asyncio
import subprocess
from metagpt.actions import Action
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger

# 代码撰写Action
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
        prompt = self.PROMPT_TEMPLATE.format(requirements=requirements)
        rsp = await self._aask(prompt)
        code_text = CodeWrite.parse_code(rsp)
        return code_text

    @staticmethod
    def parse_code(rsp): # 从模型生成中字符串匹配提取生成的代码
        pattern = r'```python(.*?)```'  # 使用非贪婪匹配
        match = re.search(pattern, rsp, re.DOTALL)
        code_text = match.group(1) if match else rsp
        return code_text


# 需求优化Action
class RequirementsOpt(Action):
    PROMPT_TEMPLATE: str = """
    你要遵守的规范有：
    1.简要说明 (Brief Description)
　　简要介绍该用例的作用和目的。
　　2.事件流 (Flow of Event)
　　包括基本流和备选流，事件流应该表示出所有的场景。
　　3.用例场景 (Use-Case Scenario)
　　包括成功场景和失败场景，场景主要是由基本流和备选流组合而成的。
　　4.特殊需求 (Special Requirement)
　　描述与该用例相关的非功能性需求（包括性能、可靠性、可用性和可扩展性等）和设计约束（所使用的操作系统、开发工具等）。
　　5.前置条件 (Pre-Condition)
　　执行用例之前系统必须所处的状态。
　　6.后置条件 (Post-Condition)
　　用例执行完毕后系统可能处于的一组状态。
    无需测试用例，所有的代码在一个```python```中
　　请优化以下需求，使其更加明确和全面：
    {requirements}
    """

    name: str = "RequirementsOpt"

    async def run(self, requirements: str):
        prompt = self.PROMPT_TEMPLATE.format(requirements=requirements)
        rsp = await self._aask(prompt)
        return rsp.strip()  # 返回优化后的需求


# 代码运行Action
class CodeRun(Action):
    name: str = "CodeRun"

    async def run(self, code_text: str):
        try:
            result = subprocess.run(
                ['python', '-c', code_text],
                text=True,
                capture_output=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            return e.stderr


# 设计Programmer Agent人设
class Programmer(Role):
    """
    Programmer 角色类，继承自 Role 基类
    """

    name: str = "cheems"
    profile: str = "Programmer"

    def __init__(self, **kwargs):
        """
        初始化 Programmer 角色
        """
        super().__init__(**kwargs)  # 调用基类构造函数
        self.set_actions([RequirementsOpt, CodeWrite, CodeRun])  # 为角色配备三个动作
        self._set_react_mode(react_mode="by_order") # 顺序执行

    async def _act(self) -> Message:
        """
        定义角色行动逻辑
        """
        logger.info(f"{self._setting}: 准备 {self.rc.todo}")  # 记录日志
        todo = self.rc.todo  # 按照排列顺序获取待执行的动作

        msg = self.get_memories(k=1)[0]  # 获取最相似的一条记忆 (用户输入)

        # 优化需求》编写代码》运行代码
        result = await todo.run(msg.content)

        # 构造 Message 对象
        msg = Message(content=result, role=self.profile, cause_by=type(todo))
        self.rc.memory.add(msg) # 将运行结果添加到记忆

        return msg  # 返回最终的 Message
        
# 运行我们的Agent
async def main():
    msg = "如何用python设计一个ToDoList，使用Tkinter库，尽量不要安装额外包，安装包的代码要直接在python代码中运行，而非手动输入cmd;"
    role = Programmer()  # 实例化 Programmer
    logger.info(msg)  # 记录日志信息
    result = await role.run(msg)  # 得到运行结果
    logger.info(result)  # 记录运行结果

asyncio.run(main())  # 异步运行 main 函数