from typing import Any, Dict

from app.models.exam import StudentResponse
from app.utils.prompts import get_system_prompt


class AssistantService:
    def __init__(self):
        self.functions = {
            "determine_intention_evaluation": {
                "name": "determine_intention_evaluation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "intention": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
                        "evaluation": {"type": "integer", "minimum": 1, "maximum": 5},
                    },
                },
            }
        }

    async def process_response(
        self, response: str, context: Dict[str, Any]
    ) -> StudentResponse:
        messages = [
            {"role": "system", "content": get_system_prompt()},
            {"role": "user", "content": f"Student response: {response}"},
        ]

        result = await self._call_openai(messages)
        return StudentResponse(**result)
