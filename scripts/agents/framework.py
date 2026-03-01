import re

class Tool:
    def __init__(self, name, func, description):
        self.name = name
        self.func = func
        self.description = description

    def run(self, *args, **kwargs):
        return self.func(*args, **kwargs)

class Agent:
    def __init__(self, name, tools, system_prompt=""):
        self.name = name
        self.tools = {t.name: t for t in tools}
        self.system_prompt = system_prompt

    def process(self, user_input):
        # Simple keyword-based tool selection for POC
        # In a real LLM agent, this would call the LLM to decide.
        # Here we mock the "reasoning" logic.
        pass

class Supervisor(Agent):
    def __init__(self, agents):
        self.agents = {a.name: a for a in agents}
        super().__init__("Supervisor", [], "I route requests to the right agent.")

    def route(self, user_input):
        user_input = user_input.lower()
        if "gap" in user_input or "member" in user_input or "trace" in user_input:
            return self.agents["DataAgent"]
        elif "why" in user_input or "explain" in user_input or "rule" in user_input:
            return self.agents["GapAgent"]
        else:
            return None
