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
4. QUESTIONING -> CHAT: When student gives meaningless/random answers
5. EXPLAINING -> QUESTIONING: Only after student confirms understanding
6. EXPLAINING -> CHAT: When student is not engaging seriously
7. QUESTIONING -> QUESTIONING: After normal response
8. QUESTIONING -> EVALUATING: When completed

Key indicators for CHAT state:
- Meaningless responses (e.g., "xxxx", "???", random characters)
- Off-topic responses
- Non-serious engagement
- Random keyboard input
- Repeated short/meaningless answers

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
5. Chat indicators: Random input, meaningless responses, non-academic conversation

Confidence levels:
1: Very uncertain - Response is unclear or ambiguous
2: Somewhat uncertain - Response gives some hints but not clear
3: Moderately confident - Response provides reasonable indication
4: Quite confident - Response gives clear indication
5: Very confident - Response gives explicit indication

For QUESTIONING state:
- Move to CHAT if:
  * Student gives meaningless answers (e.g., "hehe", "???", random letters)
  * Student is not engaging with the question
  * Response is completely off-topic
  * Response shows no attempt to answer academically
- Stay in QUESTIONING if the answer is relevant to the question
- Move to EXPLAINING if student shows confusion
"""


def analyze_response(
    student_response: str, current_state: ExamState, context: dict = None
) -> StateResponse:
    """Analyze student response and determine next state"""
    # Create a new context dictionary, only containing serializable data
    serializable_context = {
        "questions_answered": context.get("questions_answered", 0),
        "hints_requested": context.get("hints_requested", 0),
        "current_difficulty": context.get("current_difficulty", 3),
        "topic": context.get("topic"),
        "subtopic": context.get("subtopic"),
    }

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"""
Current state: {current_state}
Student response: "{student_response}"
Context: {json.dumps(serializable_context)}

Determine the next state based on this response.
If in EXPLAINING state, carefully check if student needs more explanation or is ready to continue.
For INIT state:
- Stay in INIT if just greeting or casual conversation
- Move to TOPIC_SELECTED only when a specific topic is mentioned
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

    # Special handling for INIT state
    if current_state == ExamState.INIT:
        # Check if response is just a greeting
        greetings = ["hi", "hello", "hey", "good morning", "good afternoon"]
        if student_response.lower().strip() in greetings:
            result["next_state"] = ExamState.INIT.value
            result["reason"] = "Simple greeting, waiting for topic selection"
            return StateResponse(**result)

    return StateResponse(**result)


def main():
    state_machine = ExamStateMachine()

    while True:
        # Always display current state
        print(f"\nCurrent State: {state_machine.get_current_state()}")
        print(f"Context: {state_machine.get_context()}")

        student_response = input("\nStudent: ")
        if student_response.lower() == "exit":
            break

        # Analyze response
        result = analyze_response(
            student_response,
            state_machine.get_current_state(),
            state_machine.get_context(),
        )

        try:
            # Attempt state transition
            state_machine.transition(
                result.next_state,
                metadata={
                    "confidence": result.confidence,
                    "reason": result.reason,
                    "topic": getattr(result, "topic", None),
                },
            )

        except ValueError as e:
            print(f"Invalid transition: {e}")
            continue  # Continue loop but don't update state


if __name__ == "__main__":
    main()
