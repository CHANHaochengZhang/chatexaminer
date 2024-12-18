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
from app.models.state_machine import ExamState, ExamStateMachine, StateResponse

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
1. INIT -> TOPIC_SELECTED: When student greets or shows readiness
2. TOPIC_SELECTED -> QUESTIONING: When student indicates readiness to start exam
3. QUESTIONING -> EXPLAINING: When student shows confusion
4. EXPLAINING -> QUESTIONING: After providing explanation
5. QUESTIONING -> QUESTIONING: After normal response
6. QUESTIONING -> EVALUATING: When completed

Key indicators for TOPIC_SELECTED -> QUESTIONING:
- Student asks for questions
- Student indicates readiness to begin
- Student confirms topic selection

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
If in TOPIC_SELECTED state and student is ready to start, transition to QUESTIONING.
If transitioning to TOPIC_SELECTED state, you must identify the topic.
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

    # 如果在 TOPIC_SELECTED 状态且学生准备开始，转到 QUESTIONING
    if current_state == ExamState.TOPIC_SELECTED and any(
        keyword in student_response.lower()
        for keyword in ["start", "begin", "question", "ready", "let's go"]
    ):
        result["next_state"] = ExamState.QUESTIONING.value

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
