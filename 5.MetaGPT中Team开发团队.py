import re
import fire # 新增了招募
from metagpt.actions import Action, UserRequirement
from metagpt.logs import logger
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.team import Team
import subprocess
# 加载环境变量
from dotenv import load_dotenv 
load_dotenv()

# 需求分析优化Action
class RequirementsOptAction(Action):
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
　　请优化以下需求，使其更加明确和全面：
    {requirements}
    """

    name: str = "RequirementsOpt"

    async def run(self, requirements: str):
        prompt = self.PROMPT_TEMPLATE.format(requirements=requirements)
        rsp = await self._aask(prompt)
        return rsp.strip()  # 返回优化后的需求

# 代码撰写Action
class CodeWriteAction(Action):
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
        code_text = CodeWriteAction.parse_code(rsp)
        return code_text

    @staticmethod
    def parse_code(rsp): # 从模型生成中字符串匹配提取生成的代码
        pattern = r'```python(.*?)```'  # 使用非贪婪匹配
        match = re.search(pattern, rsp, re.DOTALL)
        code_text = match.group(1) if match else rsp
        return code_text
        
# 代码测试Action
class CodeTestAction(Action):
    PROMPT_TEMPLATE: str = """
    上下文：{context}
    为给定的函数编写 {k} 个单元测试，并且假设你已经导入了该函数。
    返回 ```python 您的测试代码 ```，且不包含其他文本。
    your code:
    """
    name: str = "CodeTest"

    async def run(self, context: str, k: int = 5):
        prompt = self.PROMPT_TEMPLATE.format(context=context, k=k)

        rsp = await self._aask(prompt)

        code_text = CodeWriteAction.parse_code(rsp)

        return code_text




class CodeReviewAction(Action):
    PROMPT_TEMPLATE: str = """
    context：{context}
    审查测试用例并提供一个关键性的review,在评论中，请包括对测试用例覆盖率的评估，以及对测试用例的可维护性和可读性的评估。同时，请提供具体的改进建议。
    """

    name: str = "CodeReview"

    async def run(self, context: str):
        prompt = self.PROMPT_TEMPLATE.format(context=context)

        rsp = await self._aask(prompt)

        return rsp
class RA(Role): #需求分析师缩写
    name: str = "yake"
    profile: str = "Requirement Analysis"
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._watch([UserRequirement])
        self.set_actions([RequirementsOptAction])
        
class Coder(Role):
    name: str = "cheems"
    profile: str = "Coder"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._watch([RequirementsOptAction])
        self.set_actions([CodeWriteAction])
        
class Tester(Role):
    name: str = "Bob"
    profile: str = "Tester"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([CodeTestAction])
        # self._watch([SimpleWriteCode])
        self._watch([CodeWriteAction,CodeReviewAction])  # 这里测试一下同时监听两个动作是什么效果

    async def _act(self) -> Message:
        logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")
        todo = self.rc.todo

        # context = self.get_memories(k=1)[0].content # use the most recent memory as context
        context = self.get_memories()  # 获取所有记忆，避免重复检查

        code_text = await todo.run(context, k=5)  # specify arguments
        msg = Message(content=code_text, role=self.profile, cause_by=type(todo))

        return msg

class Reviewer(Role):
    name: str = "Charlie"
    profile: str = "Reviewer"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([CodeReviewAction])
        self._watch([CodeTestAction])
        


async def main(
    idea: str = "撰写一个python自动生成随机人物数据并保存到csv的tkinter程序,用户输入数量，则随机生成人物信息保存csv到当前文件夹下",
    investment: float = 3.0, # token限制3美金
    n_round: int = 5, # 循环5 轮
    add_human: bool = False, # 无需用户参与评审
):
    logger.info(idea)

    team = Team()
    team.hire(
        [
        	RA(),
            Coder(),
            Tester(),
            Reviewer(is_human=add_human),
        ]
    )

    team.invest(investment=investment) # 计算成本预算
    team.run_project(idea) # 初始化项目
    await team.run(n_round=n_round) # 开始循环

if __name__ == "__main__":
    fire.Fire(main)