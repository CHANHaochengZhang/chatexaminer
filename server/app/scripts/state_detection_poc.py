import json
import sys
from enum import Enum
from pathlib import Path
from typing import Literal

import openai
from pydantic import BaseModel

# Add server directory to Python path
SERVER_DIR = Path(__file__).parent.parent.parent
sys.path.append(str(SERVER_DIR))

from app.core.config import settings
from app.models.state_machine import ExamStateMachine, StateResponse


class ExamState(str, Enum):
    INIT = "INIT"
    TOPIC_SELECTED = "TOPIC_SELECTED"
    QUESTIONING = "QUESTIONING"
    EXPLAINING = "EXPLAINING"
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"


functions = [
    {
        "name": "determine_state",
        "description": "Determine the next state based on student's response",
        "parameters": {
            "type": "object",
            "properties": {
                "next_state": {
                    "type": "string",
                    "enum": [state.value for state in ExamState],
                    "description": "The next state to transition to",
                },
                "confidence": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Confidence level in state determination",
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for choosing this state",
                },
            },
            "required": ["next_state", "confidence", "reason"],
        },
    }
]

system_prompt = """You are an AI exam state analyzer. Determine the next state based on the student's response.

State Machine Rules:
1. INIT -> TOPIC_SELECTED: When topic is selected
2. TOPIC_SELECTED -> QUESTIONING: When exam starts
3. QUESTIONING -> EXPLAINING: When student shows confusion or requests clarification
4. EXPLAINING -> QUESTIONING: After providing explanation
5. QUESTIONING -> QUESTIONING: After normal response, continue with next question
6. QUESTIONING -> EVALUATING: When required questions are completed
7. EVALUATING -> COMPLETED: After generating final evaluation

Context tracking:
- Number of questions answered
- Number of hints requested
- Current difficulty level (1-5)
- Response quality history
- Topic and subtopic

Key indicators:
1. Confusion indicators: "I don't understand", "Could you explain", "What does X mean"
2. Normal response indicators: Direct answers, explanations, reasoning
3. Off-topic indicators: Break requests, unrelated questions
4. Completion indicators: Final question answered, evaluation complete

Confidence levels:
1: Very uncertain - Response is unclear or ambiguous
2: Somewhat uncertain - Response gives some hints but not clear
3: Moderately confident - Response provides reasonable indication
4: Quite confident - Response gives clear indication
5: Very confident - Response gives explicit indication

Current context will be provided in each request."""


def analyze_response(
    student_response: str, current_state: ExamState, context: dict = None
) -> StateResponse:
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"""
Current state: {current_state}
Student response: "{student_response}"
Context: {json.dumps(context) if context else 'No additional context'}

Determine the next state based on this response.
""",
        },
    ]

    response = openai.chat.completions.create(
        model="gpt-4o-mini-2024-07-18",
        messages=messages,
        functions=functions,
        function_call={"name": "determine_state"},
    )

    result = json.loads(response.choices[0].message.function_call.arguments)
    return StateResponse(**result)


def main():
    state_machine = ExamStateMachine()

    while True:
        # 始终显示当前状态
        print(f"\nCurrent State: {state_machine.get_current_state()}")
        print(f"Context: {state_machine.get_context()}")

        student_response = input("\nStudent: ")
        if student_response.lower() == "exit":
            break

        # 分析响应
        result = analyze_response(
            student_response,
            state_machine.get_current_state(),
            state_machine.get_context(),
        )

        try:
            # 尝试转换状态
            state_machine.transition(
                result.next_state,
                metadata={"confidence": result.confidence, "reason": result.reason},
            )

        except ValueError as e:
            print(f"Invalid transition: {e}")
            continue  # 继续下一次循环，但不更新状态


if __name__ == "__main__":
    main()
