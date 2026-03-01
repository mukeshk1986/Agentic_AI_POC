from scripts.agents.framework import Agent, Tool

def explain_pharmacy_gap():
    return "A Pharmacy Gap occurs when a member fills a prescription for a chronic condition (e.g., Diabetes) but has no corresponding diagnosis code in their medical history. This suggests the condition is undocumented."

def explain_procedure_gap():
    return "A Procedure Gap occurs when a member undergoes a medical procedure associated with a chronic condition, but has no diagnosis code for that condition recorded in the last 180 days."

tools = [
    Tool("explain_pharmacy_gap", explain_pharmacy_gap, "Explain logic for pharmacy gaps"),
    Tool("explain_procedure_gap", explain_procedure_gap, "Explain logic for procedure gaps")
]

class GapAgent(Agent):
    def __init__(self):
        super().__init__("GapAgent", tools, "I explain the clinical rules for gap identification.")

    def process(self, user_input):
        if "pharmacy" in user_input.lower():
            return self.tools["explain_pharmacy_gap"].run()
        elif "procedure" in user_input.lower():
            return self.tools["explain_procedure_gap"].run()
        return "I can explain 'pharmacy' or 'procedure' gaps."
