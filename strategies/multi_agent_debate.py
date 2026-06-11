"""
Multi-Agent Debate strategy.
Based on: https://arxiv.org/abs/2305.14325

Multiple LLM agents independently reason about the same problem,
then engage in multi-round discussion, critiquing and refining
each other's reasoning. Final answer is aggregated from the last round.

Harness Engineering integration:
- Instructions: each agent has a distinct role prompt (e.g., cautious checker, creative solver)
- State: tracks per-agent, per-round reasoning and answers
- Feedback: agents critique each other's outputs, forming a feedback loop
- Environment: the debate arena where agents interact
"""
import os
from collections import Counter
from typing import Dict, Any, List

from .base import BaseStrategy


class MultiAgentDebateStrategy(BaseStrategy):
    """Multi-Agent Debate: independent reasoning + multi-round critique + final vote."""

    def harness_subsystems(self) -> Dict[str, bool]:
        return {
            "instructions": True,   # distinct role prompts per agent
            "tools": False,
            "environment": True,    # debate arena + voting environment
            "state": True,          # per-agent per-round reasoning tracked
            "feedback": True,       # inter-agent critique loop
        }

    def __init__(
        self,
        model,
        task,
        prompt_template_path: str = "prompts/base_cot.txt",
        n_agents: int = 3,
        n_rounds: int = 2,
        temperature: float = 0.7,
        **kwargs
    ):
        super().__init__(name="multi_agent_debate", model=model, task=task, **kwargs)
        self.n_agents = n_agents
        self.n_rounds = n_rounds
        self.temperature = temperature
        self.prompt_template_path = prompt_template_path
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        if not os.path.exists(self.prompt_template_path):
            return (
                "You are solving a math word problem. Think step by step and explain your reasoning clearly.\n\n"
                "Question: {question}\n"
                "Options: {options}\n\n"
                "At the end of your response, you must state your final answer choice on a single line in exactly this format:\n"
                "Answer: X\n"
                "where X is one of A, B, C, D, or E."
            )
        with open(self.prompt_template_path, "r", encoding="utf-8") as f:
            return f.read()

    def _build_agent_prompt(
        self,
        agent_id: int,
        question: str,
        options_text: str,
        round_num: int,
        other_opinions: List[str],
    ) -> str:
        """Build prompt for a specific agent in a specific round."""
        role = self._get_agent_role(agent_id)
        header = f"You are Agent {agent_id + 1}, a {role}.\n\n"

        if round_num > 0 and other_opinions:
            critique_block = "Other agents' reasoning from the previous round:\n"
            for idx, opinion in enumerate(other_opinions):
                if idx != agent_id:
                    critique_block += f"Agent {idx + 1} said:\n{opinion}\n\n"
            critique_block += (
                "Critically evaluate the above reasoning. If you disagree, explain why. "
                "Then provide your own step-by-step reasoning.\n\n"
            )
        else:
            critique_block = ""

        base = self.prompt_template.format(question=question, options=options_text)
        return header + critique_block + base

    def _get_agent_role(self, agent_id: int) -> str:
        """Assign distinct roles to agents for diverse reasoning."""
        roles = [
            "careful analytical reasoner who double-checks every step",
            "creative problem solver who looks for elegant shortcuts",
            "skeptical critic who questions assumptions and looks for traps",
        ]
        return roles[agent_id % len(roles)]

    def run(self, example: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        question = example.get("question", "")
        options = example.get("options", [])
        options_text = " ".join(options)

        n_agents = kwargs.get("n_agents", self.n_agents)
        n_rounds = kwargs.get("n_rounds", self.n_rounds)
        temp = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", 1024)

        # State tracking
        debate_history: List[List[Dict[str, Any]]] = []

        for round_num in range(n_rounds):
            print(f"    [Debate] Round {round_num + 1}/{n_rounds}")
            round_outputs: List[Dict[str, Any]] = []
            other_opinions = []
            if round_num > 0:
                other_opinions = [r["output"] for r in debate_history[-1]]

            for agent_id in range(n_agents):
                print(f"      Agent {agent_id + 1}/{n_agents} thinking...", end=" ")
                prompt = self._build_agent_prompt(
                    agent_id=agent_id,
                    question=question,
                    options_text=options_text,
                    round_num=round_num,
                    other_opinions=other_opinions,
                )
                outputs = self.model.generate(
                    prompt,
                    temperature=temp,
                    max_tokens=max_tokens,
                    n=1,
                )
                raw = outputs[0] if outputs else ""
                prediction = self.task.extract_answer(raw)
                print(f"→ {prediction}")
                round_outputs.append({
                    "agent_id": agent_id,
                    "output": raw,
                    "prediction": prediction,
                    "prompt": prompt,
                })
            debate_history.append(round_outputs)

        # Final aggregation: majority vote over last round predictions
        last_round = debate_history[-1]
        predictions = [r["prediction"] for r in last_round if r["prediction"]]
        vote_counts = Counter(predictions)
        if vote_counts:
            final_prediction = vote_counts.most_common(1)[0][0]
        else:
            final_prediction = ""

        # Build summary
        summary_lines = [
            f"=== Multi-Agent Debate ({n_agents} agents, {n_rounds} rounds) ===",
            f"Final Answer: {final_prediction}",
            f"Votes: {dict(vote_counts)}",
            "",
        ]
        for round_idx, round_data in enumerate(debate_history):
            summary_lines.append(f"--- Round {round_idx + 1} ---")
            for agent_data in round_data:
                summary_lines.append(
                    f"Agent {agent_data['agent_id'] + 1} (→ {agent_data['prediction']}):\n"
                    f"{agent_data['output'][:200]}..."
                )
        summary_output = "\n".join(summary_lines)

        return {
            "prediction": final_prediction,
            "output": summary_output,
            "metadata": {
                "n_agents": n_agents,
                "n_rounds": n_rounds,
                "debate_history": debate_history,
                "vote_counts": dict(vote_counts),
            },
        }
