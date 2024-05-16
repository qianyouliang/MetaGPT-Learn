import re
import asyncio
import subprocess
from metagpt.actions import Action
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger

# 代码撰写Action
class RolePrinter(Action):
    PROMPT_TEMPLATE: str = """
    我是{name}，{birth}岁，我已经来到这个世界{day}天了，我现在身份是{role}，等级为{level},这些天，我的经历是{history}，我将要去做{goal}
    """

    name: str = "CodeWriter"

    async def run(self, name: str,birth:int,day:int,role:str,level:int,history:str,goal:str):
        prompt = self.PROMPT_TEMPLATE.format(name=name,birth=birth,day=day,role=role,level=level,history=history,goal=goal)
        rsp = await self._aask(prompt)
        code_text = CodeWrite.parse_code(rsp)
        return code_text

    @staticmethod
    def parse_code(rsp): # 从模型生成中字符串匹配提取生成的代码
        pattern = r'```python(.*?)```'  # 使用非贪婪匹配
        match = re.search(pattern, rsp, re.DOTALL)
        code_text = match.group(1) if match else rsp
        return code_text




class CustomAgent:
    def __init__(Role):
        self.actions = []
        self.memory = []
        self.execution_count = 0
        # 设定角色属性
        self.level = 1  # 修炼等级，初始为1
        self.world_view = "仙侠世界"
        self.name = "未觉醒修炼者"
        self.personality = "性格狠辣"
        self.status = "初学者"

        # 初始化动作
        self.set_actions(self.generate_initial_actions())

    def generate_new_action(self, actions: List[Action]):
        self.actions = actions
        self.current_action_index = 0

    def generate_initial_actions(self):
        prompts = [
            self.generate_prompt("我重生了，我回到了我14岁时候"),
            self.generate_prompt("距离域外天魔，入侵还有5年"),
            self.generate_prompt("我现在是捷克城的平民，是一个拥有空间天赋的未觉醒异能者，我需要尽快强大起来，先从吃饱饭开始，可是我身无分文...")
        ]
        return [Action(str(uuid.uuid4()), f"Print{i+1}", prompts[i]) for i in range(3)]

    def generate_prompt(self, event):
        return (f"你是{self.name}, 现在正处于{self.world_view}, 你的性格是{self.personality}, "
                f"你当前身份是{self.status}, 你在世界的地位是{self.level}, 面对{event}, "
                "你打算说：")

    async def _ask(self, prompt):
        # 模拟从外部获取内容
        return f"这是对提示 [{prompt}] 的响应内容。"

    async def store_to_ceramic(self, action_id, content):
        # 模拟将数据存储到Ceramic网络
        print(f"Storing action {action_id} content to Ceramic: {content}")

    def reflect_and_update(self):
        # 简单的反思机制，根据记忆更新角色属性
        if self.execution_count % 5 == 0:
            self.level += 1  # 每执行两轮，修炼等级提升一级
            self.status = "高级修炼者" if self.level > 1 else "初学者"
        print(f"反思：当前修炼等级为 {self.level}")

    async def _act(self):
        while self.current_action_index < len(self.actions):
            action = self.actions[self.current_action_index]
            result = await action.run(self)
            self.current_action_index += 1

            # 存储运行结果到记忆中
            self.memory.append({
                'id': action.id,
                'name': action.name,
                'content': result,
                'state': action.state
            })

            # 打印日志
            print(f"Action {self.current_action_index} completed: {result}")

        # 动作执行完毕后生成新的动作列表
        if self.current_action_index >= len(self.actions):
            self.execution_count += 1
            if self.execution_count < 10:  # 循环执行10次
                self.reflect_and_update()
                print("All initial actions completed. Generating new actions.")
                new_actions = [Action(str(uuid.uuid4()), "Print4", self.generate_prompt("打印4")),
                               Action(str(uuid.uuid4()), "Print5", self.generate_prompt("打印5")),
                               Action(str(uuid.uuid4()), "Print6", self.generate_prompt("打印6"))]
                self.set_actions(new_actions)
                await self._act()  # 递归调用继续执行新动作

    async def run(self):
        print(f"Agent {self.name} started in {self.world_view}.")
        await self._act()
        print(f"Agent {self.name} finished all actions with level {self.level}.")


# 运行我们的 Agent
async def main():
    agent = CustomAgent()  # 实例化 CustomAgent
    await agent.run()  # 运行 agent

asyncio.run(main())  # 异步运行 main