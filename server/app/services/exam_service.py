import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import openai
from app.core.config import settings
from app.models.evaluation import EvaluationMetrics
from app.models.exam import ExamSession
from app.models.state_machine import ExamState, ExamStateMachine
from app.services.evaluation_service import EvaluationService


class ExamService:
    def __init__(self):
        self.state_machine = ExamStateMachine()
        self.questions_file = Path(settings.QUESTIONS_FILE)
        self.evaluation_service = EvaluationService()
        self.exam_start_time = None
        self.question_start_time = None
        self.current_topic = None
        self.topic_key_points = {}  # Store key points for each topic
        self.session_metrics = {
            "questions_answered": 0,
            "hints_requested": 0,
            "response_consistency": 1.0,
            "topic_progress": {},
        }
        # Define function calling for each state
        self.state_functions = {
            ExamState.INIT: {
                "name": "handle_init_state",
                "description": "Handle initial state interaction",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "is_greeting": {"type": "boolean"},
                        "topic_mentioned": {"type": "boolean"},
                        "topic": {"type": "string", "description": "Topic mentioned by student"},
                        "next_state": {
                            "type": "string",
                            "enum": [state.value for state in ExamState],
                        },
                    },
                    "required": ["next_state"],
                },
            },
            ExamState.TOPIC_SELECTED: {
                "name": "handle_topic_selected",
                "description": "Handle topic selected state interaction",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "is_ready": {"type": "boolean"},
                        "needs_preparation": {"type": "boolean"},
                        "next_state": {
                            "type": "string",
                            "enum": [state.value for state in ExamState],
                        },
                    },
                    "required": ["next_state", "is_ready"],
                },
            },
            ExamState.QUESTIONING: {
                "name": "handle_questioning",
                "description": "Handle questioning state interaction",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "answer_quality": {"type": "integer", "minimum": 1, "maximum": 5},
                        "needs_explanation": {"type": "boolean"},
                        "wants_to_end": {"type": "boolean"},
                        "next_state": {
                            "type": "string",
                            "enum": [state.value for state in ExamState],
                        },
                    },
                    "required": ["next_state", "answer_quality"],
                },
            },
            ExamState.EXPLAINING: {
                "name": "handle_explaining",
                "description": "Handle explaining state interaction",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "understood": {"type": "boolean"},
                        "needs_more_explanation": {"type": "boolean"},
                        "next_state": {
                            "type": "string",
                            "enum": [state.value for state in ExamState],
                        },
                    },
                    "required": ["next_state", "understood"],
                },
            },
            ExamState.CHAT: {
                "name": "handle_chat_state",
                "description": "Handle chat state interaction and determine if user wants to return to previous state",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "wants_to_return": {
                            "type": "boolean",
                            "description": "Whether user indicates readiness to return (e.g., by saying 'continue', 'ready', 'ok', 'understand')",
                        },
                        "needs_explanation": {
                            "type": "boolean",
                            "description": "Whether user needs more explanation",
                        },
                        "return_state": {
                            "type": "string",
                            "enum": [state.value for state in ExamState],
                            "description": "State to return to if wants_to_return is true",
                        },
                        "chat_response": {
                            "type": "string",
                            "description": "Response to give to the user in chat mode",
                        },
                    },
                    "required": ["wants_to_return", "chat_response"],
                },
            },
            ExamState.EVALUATING: {
                "name": "handle_evaluating_state",
                "description": "Handle evaluating state interaction",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ready_for_evaluation": {"type": "boolean"},
                        "next_state": {
                            "type": "string",
                            "enum": [state.value for state in ExamState],
                        },
                    },
                    "required": ["next_state", "ready_for_evaluation"],
                },
            },
        }

    async def start_exam(self, topic: str) -> Dict:
        """Start the exam"""
        if not self.questions_file.exists():
            raise FileNotFoundError("Questions file not found")

        # Validate if topic is valid
        with open(self.questions_file, "r", encoding="utf-8") as f:
            questions = json.load(f)
            valid_topics = {q["topic"] for q in questions.values()}

        if topic not in valid_topics:
            raise ValueError(f"Invalid topic. Available topics: {', '.join(valid_topics)}")

        # Initialize exam session
        self.exam_start_time = time.time()
        self.current_topic = topic
        self.state_machine.start_exam(topic, self.questions_file)

        # Extract topic key points from questions file
        self._extract_topic_key_points(topic)

        # Record start time
        self.question_start_time = time.time()

        return self.get_next_interaction()

    def _extract_topic_key_points(self, topic: str):
        """Extract key points for the topic from questions file"""
        with open(self.questions_file, "r", encoding="utf-8") as f:
            questions = json.load(f)

        topic_questions = [q for q in questions.values() if q["topic"] == topic]
        key_points = set()

        for q in topic_questions:
            # Extract key points from correct answers
            correct_answer = q["expected_answers"]["correct"]["example"]
            # More complex NLP methods could be used here to extract key points
            # Simple example: split sentences and extract key phrases
            points = [p.strip() for p in correct_answer.split(".") if p.strip()]
            key_points.update(points)

        self.topic_key_points[topic] = list(key_points)

    def get_next_interaction(self) -> Dict:
        """Get next interaction content"""
        state = self.state_machine.get_current_state()

        if state == ExamState.QUESTIONING:
            question = self.state_machine.get_current_question()
            if question:
                self.question_start_time = time.time()
                return {
                    "type": "question",
                    "content": question["question"],
                    "question_id": question["question_id"],
                    "difficulty": question["difficulty"],
                    "context": question.get("context", []),  # Provide context for reference
                    "topic": question["topic"],
                }
            else:
                # All questions completed, generate final evaluation
                final_evaluation = self._generate_final_evaluation()
                self.state_machine.transition(ExamState.EVALUATING)
                return {
                    "type": "complete",
                    "content": "Exam completed, generating evaluation report...",
                    "evaluation": final_evaluation,
                }

        return {"type": "state_change", "state": state.value}

    async def detect_state(self, response: str, current_state: ExamState) -> Dict:
        """Detect next state based on student's response using AI"""
        print(f"\n=== 检测状态 ===")
        print(f"当前状态: {current_state}")
        print(f"学生回答: {response}")

        # Create a serializable version of session metrics
        serializable_metrics = {
            "questions_answered": self.session_metrics["questions_answered"],
            "hints_requested": self.session_metrics["hints_requested"],
            "response_consistency": self.session_metrics["response_consistency"],
        }
        print(f"会话指标: {serializable_metrics}")

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
- Meaningless responses (e.g."???", random characters)
- Off-topic responses
- Non-serious engagement
- Random keyboard input
- Repeated short/meaningless answers

For QUESTIONING state:
- Move to CHAT if:
  * Student gives meaningless answers (e.g., "hehe", "???", random letters)
  * Student is not engaging with the question
  * Response is completely off-topic
  * Response shows no attempt to answer academically
- Stay in QUESTIONING if the answer is relevant to the question
- Move to EXPLAINING if student shows confusion"""

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"""Current state: {current_state}
Student response: "{response}"
Context: {json.dumps(serializable_metrics)}

Determine the next state based on this response.""",
            },
        ]

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            functions=self.state_detection_functions,
            function_call={"name": "determine_state"},
        )

        result = json.loads(response.choices[0].message.function_call.arguments)
        print(f"状态检测结果: {result}")
        return result

    async def request_hint(self) -> Dict:
        """Request a hint for the current question"""
        print("\n=== Processing hint request ===")
        self.session_metrics["hints_requested"] += 1
        current_question = self.state_machine.get_current_question()

        if not current_question:
            return {"error": "No active question"}

        # 创建提示生成的prompt
        prompt = f"""Based on the following question metadata, generate a helpful hint that guides the student towards the answer without directly giving it away.

Question: {current_question['question']}
Topic: {current_question['topic']}
Subtopic: {current_question['subtopic']}
Difficulty: {current_question['difficulty']} (on a scale of 1-5)
Context: {current_question.get('context', [])}

Requirements for the hint:
1. Be specific to the question's topic and difficulty level
2. Guide thinking without revealing the answer
3. Reference relevant concepts from the context
4. For higher difficulty questions (4-5), focus on methodology
5. For lower difficulty questions (1-3), focus on key concepts
6. Keep the hint concise and clear

Generate a hint:"""

        # 调用OpenAI API生成hint
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert exam tutor, skilled at providing helpful hints that guide students to discover answers themselves.",
                },
                {"role": "user", "content": prompt},
            ],
        )

        hint = response.choices[0].message.content.strip()
        print(
            f"Generated hint for question {current_question['question_id']}, Hints used: {self.session_metrics['hints_requested']}"
        )

        return {
            "hint": hint,
            "question_id": current_question["question_id"],
            "hints_used": self.session_metrics["hints_requested"],
        }

    async def process_answer(self, answer: str) -> Dict:
        """Process student's answer and return next interaction"""
        current_state = self.state_machine.get_current_state()
        print(f"\n=== Processing answer ===")
        print(f"Current state: {current_state}")
        print(f"Received answer: {answer}")

        # Create a serializable version of session metrics
        serializable_metrics = {
            "questions_answered": self.session_metrics["questions_answered"],
            "hints_requested": self.session_metrics["hints_requested"],
            "response_consistency": self.session_metrics["response_consistency"],
        }

        # Get the function definition for current state
        function_def = self.state_functions.get(current_state)
        if not function_def:
            print(f"Error: No handler found for state {current_state}")
            return {"type": "error", "message": f"No handler for state {current_state}"}

        system_prompt = f"""You are an AI exam state analyzer. Analyze the student's response in the current state.

Current State: {current_state}
Student Response: {answer}
Context: {json.dumps(serializable_metrics)}

For CHAT state:
1. Determine if student wants to return to regular exam (by saying continue, ready, ok, understand, etc.)
2. If yes, check context for previous_state to return to
3. If no previous_state exists, default to QUESTIONING
4. If student needs help, provide supportive response and stay in CHAT

For other states:
Determine the appropriate action based on the response."""

        # Call GPT with the state-specific function
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": answer},
            ],
            functions=[function_def],
            function_call={"name": function_def["name"]},
        )

        result = json.loads(response.choices[0].message.function_call.arguments)
        print(f"GPT response result: {result}")

        # Update questions_answered and evaluation when in QUESTIONING state
        if current_state == ExamState.QUESTIONING and result.get("answer_quality", 0) > 0:
            print(
                f"Updating questions answered: {self.session_metrics['questions_answered']} -> {self.session_metrics['questions_answered'] + 1}"
            )
            self.session_metrics["questions_answered"] += 1

            # Get current question
            current_question = self.state_machine.get_current_question()
            if current_question:
                # Calculate time taken
                time_taken = (
                    time.time() - self.question_start_time if self.question_start_time else 0
                )

                # Create evaluation metrics
                metrics = EvaluationMetrics(
                    accuracy=result["answer_quality"] * 20,  # Convert 1-5 score to percentage
                    clarity=result["answer_quality"] * 20,
                    understanding=result["answer_quality"] * 20,
                    hints_used=self.session_metrics["hints_requested"],  # Include actual hints used
                )

                # Update evaluation service
                print(
                    f"Adding question evaluation - ID: {current_question['question_id']}, Score: {metrics}, Hints used: {self.session_metrics['hints_requested']}"
                )
                self.evaluation_service.add_question_evaluation(
                    current_question["question_id"],
                    metrics,
                    time_taken,
                    current_question["difficulty"],
                    "Answer evaluated based on quality score",
                )

        if current_state == ExamState.CHAT:
            if result.get("wants_to_return"):
                return_state = result.get("return_state")
                if not return_state:
                    return_state = self.state_machine.context.get(
                        "previous_state", ExamState.QUESTIONING
                    )
                print(f"从CHAT状态返回到: {return_state}")
                self.state_machine.transition(return_state)
            return {"type": "chat", "content": result["chat_response"]}

        # Handle other states as before
        next_state = ExamState(result["next_state"])
        print(f"准备转换到状态: {next_state}")

        if next_state == ExamState.CHAT:
            self.state_machine.context["previous_state"] = current_state

        self.state_machine.transition(next_state)
        return self.get_next_interaction()

    def _update_topic_progress(
        self, topic: str, understanding_score: float, covered_points: List[str]
    ):
        """Update topic progress"""
        if topic not in self.session_metrics["topic_progress"]:
            self.session_metrics["topic_progress"][topic] = {
                "scores": [],
                "covered_points": set(),
                "total_points": len(self.topic_key_points.get(topic, [])),
            }

        progress = self.session_metrics["topic_progress"][topic]
        progress["scores"].append(understanding_score)
        progress["covered_points"].update(covered_points)

        # Update topic coverage in evaluation service
        self.evaluation_service.update_topic_coverage(
            topic,
            sum(progress["scores"]) / len(progress["scores"]),
            list(progress["covered_points"]),
        )

    def _update_behavior_metrics(self, time_taken: float):
        """Update behavior metrics"""
        metrics = {
            "avg_hints_per_question": self.session_metrics["hints_requested"]
            / self.session_metrics["questions_answered"],
            "avg_time_per_question": time_taken,
            "response_consistency": self._calculate_response_consistency(),
        }

        self.evaluation_service.update_behavior_score(metrics)

    def _calculate_response_consistency(self) -> float:
        """Calculate response consistency"""
        if self.session_metrics["questions_answered"] < 2:
            return 1.0

        session = self.state_machine.context["exam_session"]
        evaluations = [eval["metrics"]["understanding"] for eval in session.evaluations.values()]

        # Calculate differences between adjacent scores
        differences = [abs(evaluations[i] - evaluations[i - 1]) for i in range(1, len(evaluations))]

        # Return consistency score (1 - average difference/100)
        if not differences:  # 如果没有差异数据，返回1.0
            return 1.0

        avg_diff = sum(differences) / len(differences)
        return max(0, 1 - (avg_diff / 100))

    def _adjust_difficulty(self, metrics: EvaluationMetrics):
        """Adjust difficulty based on student performance"""
        avg_performance = (metrics.accuracy + metrics.understanding) / 2

        if avg_performance > 85:
            self.state_machine.increase_difficulty()
        elif avg_performance < 60:
            self.state_machine.decrease_difficulty()

    def _generate_final_evaluation(self) -> Dict:
        """Generate final evaluation report"""
        print("\n=== 生成最终评估报告 ===")
        final_eval = self.evaluation_service.get_final_evaluation()
        print(f"评估服务返回数据: {final_eval}")

        # Add additional evaluation information
        result = {
            "total_score": final_eval.total_score,
            "topic_coverage": final_eval.topic_coverage,
            "behavior_score": final_eval.behavior_score,
            "question_evaluations": {
                qid: {
                    "score": eval.metrics.dict(),
                    "feedback": eval.feedback,
                    "time_taken": eval.time_taken,
                }
                for qid, eval in final_eval.question_evaluations.items()
            },
            "session_metrics": {
                "total_time": time.time() - self.exam_start_time if self.exam_start_time else 0,
                "questions_answered": self.session_metrics["questions_answered"],
                "hints_used": self.session_metrics["hints_requested"],
                "response_consistency": self.session_metrics["response_consistency"],
            },
        }
        print(f"生成的评估报告: {result}")
        return result

    def get_progress_evaluation(self) -> Dict:
        """获取当前进度评估"""
        current_state = self.state_machine.get_current_state()

        # 基础统计信息
        stats = {
            "questions_answered": self.session_metrics["questions_answered"],
            "hints_requested": self.session_metrics["hints_requested"],
            "current_difficulty": self.state_machine.context.get("current_difficulty", 3),
            "current_state": current_state.value,
        }

        # 计算当前得分
        current_score = 0
        if self.evaluation_service.current_evaluation.question_evaluations:
            scores = []
            for eval in self.evaluation_service.current_evaluation.question_evaluations.values():
                question_score = (
                    eval.metrics.accuracy + eval.metrics.clarity + eval.metrics.understanding
                ) / 3
                question_score -= eval.metrics.hints_used * 10
                question_score *= eval.difficulty / 5
                scores.append(question_score)
            current_score = sum(scores) / len(scores)

        # 主题覆盖进度
        topic_progress = {}
        for topic, data in self.session_metrics["topic_progress"].items():
            if data["total_points"] > 0:
                coverage = len(data["covered_points"]) / data["total_points"] * 100
                topic_progress[topic] = {
                    "coverage": coverage,
                    "score": sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0,
                }

        # 最近的问题评估
        recent_evaluations = []
        for qid, eval in list(
            self.evaluation_service.current_evaluation.question_evaluations.items()
        )[-3:]:
            recent_evaluations.append(
                {
                    "question_id": qid,
                    "score": {
                        "accuracy": eval.metrics.accuracy,
                        "clarity": eval.metrics.clarity,
                        "understanding": eval.metrics.understanding,
                    },
                    "feedback": eval.feedback,
                    "time_taken": eval.time_taken,
                }
            )

        return {
            "stats": stats,
            "current_score": current_score,
            "topic_progress": topic_progress,
            "recent_evaluations": recent_evaluations,
            "behavior_metrics": {
                "avg_time_per_question": sum(
                    eval.time_taken
                    for eval in self.evaluation_service.current_evaluation.question_evaluations.values()
                )
                / max(1, len(self.evaluation_service.current_evaluation.question_evaluations)),
                "hint_usage_rate": self.session_metrics["hints_requested"]
                / max(1, self.session_metrics["questions_answered"]),
                "response_consistency": self._calculate_response_consistency(),
            },
        }
