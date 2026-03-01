from scripts.agents.framework import Supervisor
from scripts.agents.data_agent import DataAgent
from scripts.agents.gap_agent import GapAgent

class ClinicalSupervisor(Supervisor):
    def __init__(self):
        super().__init__([DataAgent(), GapAgent()])

    def route(self, user_input):
        user_input = user_input.lower()
        if "gap" in user_input or "member" in user_input or "trace" in user_input or "mem_" in user_input:
            # Assuming DataAgent is the correct agent for these keywords
            return self.agents["DataAgent"]
        # If no specific agent is routed, return None, and the process method will handle the default message
        return None

    def process(self, user_input):
        agent = self.route(user_input)
        if agent:
            return f"[{agent.name}]: " + agent.process(user_input)
        else:
            return "I'm not sure which agent to ask. Try asking about 'gaps', 'members', or 'explain rules'."
