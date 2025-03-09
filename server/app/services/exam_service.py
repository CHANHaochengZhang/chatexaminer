import asyncio
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import openai
from app.core.config import settings
from app.models.evaluation import EvaluationMetrics
from app.models.exam import ExamSession
from app.models.exam_record import ExamRecord
from app.models.state_machine import ExamState, ExamStateMachine
from app.services.evaluation_service import EvaluationService

MAX_EXAM_DURATION = 400  # 1小时
MAX_QUESTION_DURATION = 300  # 5分钟


class ExamService:
    def __init__(self):
        """Initialize exam service"""
        self.state_machine = ExamStateMachine()
        self.questions_file = Path(settings.QUESTIONS_FILE)
        self.evaluation_service = EvaluationService()
        self.session_id = str(uuid.uuid4())
        self.exam_start_time = time.time()
        self.question_start_time = None
        self.current_topic = None
        self.topic_key_points = {}  # Store key points for each topic
        self.session_metrics = {
            "questions_answered": 0,
            "hints_requested": 0,
            "total_time": 0,
            "response_consistency": 1.0,
            "topic_progress": {},
        }
        self.conversation_history = []  # 存储对话历史
        self.max_history_length = 10  # 存储的最大历史对话数量

        # 添加状态检测函数定义
        self.state_detection_functions = [
            {
                "name": "determine_state",
                "description": "Determine the next state based on the student's response",
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
                            "maximum": 10,
                            "description": "How confident the model is in this state determination (1-10)",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason for the state determination",
                        },
                        "wants_to_return": {
                            "type": "boolean",
                            "description": "Whether the student wants to return to a previous state (only for CHAT state)",
                        },
                        "return_state": {
                            "type": "string",
                            "enum": [state.value for state in ExamState],
                            "description": "The state to return to (only if wants_to_return is true)",
                        },
                    },
                    "required": ["next_state", "confidence", "reason"],
                },
            }
        ]

        # Define state functions for OpenAI function calling
        self.state_functions = {
            ExamState.INIT: {
                "name": "handle_init_state",
                "description": "Handle initial state interaction",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "has_topic": {"type": "boolean"},
                        "topic": {"type": "string"},
                        "next_state": {
                            "type": "string",
                            "enum": [state.value for state in ExamState],
                        },
                    },
                    "required": ["has_topic", "next_state"],
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
                "description": "Handle chat state interaction",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "wants_to_return": {"type": "boolean"},
                        "needs_explanation": {
                            "type": "boolean",
                            "description": "Whether user needs more explanation",
                        },
                        "return_state": {
                            "type": "string",
                            "enum": [state.value for state in ExamState],
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
                    "required": ["ready_for_evaluation", "next_state"],
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

    def _add_to_conversation_history(self, role: str, content: str):
        """添加消息到对话历史"""
        self.conversation_history.append({"role": role, "content": content})
        # 保持历史记录在限定数量内
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history = self.conversation_history[-self.max_history_length :]
        print(f"对话历史已更新，当前历史记录数: {len(self.conversation_history)}")

    def get_next_interaction(self) -> Dict:
        """Get next interaction content"""
        state = self.state_machine.get_current_state()

        if state == ExamState.QUESTIONING:
            question = self.state_machine.get_current_question()
            if question:
                self.question_start_time = time.time()
                # 将系统问题添加到对话历史
                self._add_to_conversation_history("assistant", question["question"])
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
        """检测学生回答对应的下一个状态"""
        print(f"\n=== 检测状态 ===")
        print(f"当前状态: {current_state}")
        print(f"学生回答: {response}")

        # 记录用户消息到对话历史
        if not hasattr(self, "conversation_history"):
            self.conversation_history = []
            self.max_history_length = 10

        # 添加用户消息到对话历史
        self._add_to_conversation_history("user", response)

        # 创建可序列化的会话指标
        serializable_metrics = {
            "questions_answered": self.session_metrics["questions_answered"],
            "hints_requested": self.session_metrics["hints_requested"],
            "response_consistency": self.session_metrics["response_consistency"],
        }
        print(f"会话指标: {serializable_metrics}")

        # 根据当前状态选择不同的提示
        if current_state == ExamState.CHAT:
            system_prompt = """You are an AI exam state analyzer. Determine if the student wants to return to the exam based on their conversation history.

Focus on identifying:
1. If the student wants to return to regular questioning
2. If they want to continue the chat
3. If they need further explanation

Use their message history to understand their intent in context."""

            # 创建带对话历史的消息列表
            messages = [{"role": "system", "content": system_prompt}]

            # 添加部分历史记录
            if len(self.conversation_history) > 1:
                recent_history = self.conversation_history[
                    -min(5, len(self.conversation_history)) :
                ]
                for msg in recent_history:
                    if msg["role"] != "user" or msg["content"] != response:  # 避免重复添加当前消息
                        messages.append(msg)

            # 添加当前用户响应作为最后一条消息
            messages.append(
                {
                    "role": "user",
                    "content": f"""Current state: {current_state}
Student response: "{response}"
Context: {json.dumps(serializable_metrics)}

Based on this interaction, determine:
1. If the student wants to return to the regular exam (set wants_to_return to true)
2. If they want to continue chatting (set wants_to_return to false)
3. What state they should return to if they want to return
""",
                }
            )
        else:
            # 标准状态检测提示
            system_prompt = """You are an AI exam state analyzer. Determine the next state based on the student's response.

State Machine Rules:
1. INIT -> TOPIC_SELECTED: When student greets or shows readiness
2. TOPIC_SELECTED -> QUESTIONING: When student indicates readiness to start exam
3. QUESTIONING -> EXPLAINING: When student shows confusion
4. QUESTIONING -> CHAT: When student gives meaningless/random answers
5. EXPLAINING -> QUESTIONING: Only after student confirms understanding
6. EXPLAINING -> CHAT: When student is not engaging seriously
7. QUESTIONING -> QUESTIONING: After normal response
8. QUESTIONING -> EVALUATING: Only when student explicitly requests to end the exam (e.g., "I want to end the exam", "I'm finished", "END_EXAM", "Let's proceed to evaluation")
9. EVALUATING -> COMPLETED: Only after evaluation is complete"""

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

        # 定义简化的状态检测函数
        functions = [
            {
                "name": "determine_state",
                "description": "Determine the next state based on the student's response",
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
                            "maximum": 10,
                            "description": "Confidence level in this determination",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reasoning behind this state determination",
                        },
                        "wants_to_return": {
                            "type": "boolean",
                            "description": "Whether the student wants to return to regular exam (CHAT state only)",
                        },
                        "return_state": {
                            "type": "string",
                            "enum": [state.value for state in ExamState],
                            "description": "State to return to if wants_to_return is true",
                        },
                    },
                    "required": ["next_state", "confidence", "reason"],
                },
            }
        ]

        # 调用API进行状态检测
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            functions=functions,
            function_call={"name": "determine_state"},
        )

        # 解析结果
        function_args = response.choices[0].message.function_call.arguments
        result = json.loads(function_args)
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
        """Process student's answer"""
        current_state = self.state_machine.get_current_state()
        print(f"\n=== Processing answer ===")
        print(f"Current state: {current_state}")
        print(f"Received answer: {answer}")

        # 添加用户消息到对话历史（确保历史记录的完整性）
        self._add_to_conversation_history("user", answer)

        # 分析回答
        result = await self._analyze_response(answer, current_state)

        # 如果学生要结束考试，直接处理状态转换
        if current_state == ExamState.QUESTIONING and result.get("wants_to_end"):
            print("学生请求结束考试，准备转换到评估状态...")
            next_state = ExamState(result["next_state"])
            self.state_machine.transition(next_state)
            return self.get_next_interaction()

        # 其他情况下继续正常处理答案
        if current_state == ExamState.QUESTIONING:
            # Update questions answered count
            old_count = self.session_metrics["questions_answered"]
            self.session_metrics["questions_answered"] = old_count + 1
            print(
                f"Updating questions answered: {old_count} -> {self.session_metrics['questions_answered']}"
            )

            # 获取上一个问题用于评估
            session = self.state_machine.context.get("exam_session")
            if session:
                question_to_evaluate = session.get_prev_question()
                if question_to_evaluate:
                    time_taken = time.time() - (self.question_start_time or time.time())
                    evaluation = await self.evaluation_service.evaluate_response(
                        question=question_to_evaluate,
                        student_response=answer,
                        hints_used=self.session_metrics["hints_requested"],
                        time_taken=time_taken,
                    )

                    # 记录评估结果
                    self.evaluation_service.add_question_evaluation(
                        question_id=question_to_evaluate["question_id"],
                        question=question_to_evaluate["question"],
                        topic=question_to_evaluate["topic"],
                        metrics=evaluation.metrics,
                        time_taken=time_taken,
                        difficulty=question_to_evaluate["difficulty"],
                        feedback=evaluation.feedback,
                        raw_response=answer,  # 添加学生的回答
                    )

        # 处理CHAT状态
        if current_state == ExamState.CHAT:
            if result.get("wants_to_return"):
                return_state = result.get("return_state")
                if not return_state:
                    return_state = self.state_machine.context.get(
                        "previous_state", ExamState.QUESTIONING
                    )
                print(f"从CHAT状态返回到: {return_state}")
                self.state_machine.transition(ExamState(return_state))
            else:
                # 添加助手回复到对话历史
                chat_response = result["chat_response"]
                self._add_to_conversation_history("assistant", chat_response)

            return {"type": "chat", "content": result["chat_response"]}

        # Handle state transition
        next_state = ExamState(result["next_state"])
        print(f"准备转换到状态: {next_state}")

        if next_state == ExamState.CHAT:
            self.state_machine.context["previous_state"] = current_state

        self.state_machine.transition(next_state)

        # 评估完当前答案后，只在非CHAT状态下获取下一题
        if current_state == ExamState.QUESTIONING and next_state != ExamState.CHAT:
            session = self.state_machine.context.get("exam_session")
            if session:
                next_question = session.get_next_question()
                if next_question:
                    return {
                        "type": "question",
                        "content": next_question["question"],
                        "question_id": next_question["question_id"],
                    }

        return self.get_next_interaction()

    async def _analyze_response(self, answer: str, current_state: ExamState) -> Dict:
        """Analyze student's response"""
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

State Machine Rules:
1. INIT -> TOPIC_SELECTED: When student greets or shows readiness
2. TOPIC_SELECTED -> QUESTIONING: When student indicates readiness to start exam
3. QUESTIONING -> EXPLAINING: When student shows confusion
4. QUESTIONING -> CHAT: When student gives meaningless/random answers
5. EXPLAINING -> QUESTIONING: Only after student confirms understanding
6. EXPLAINING -> CHAT: When student is not engaging seriously
7. QUESTIONING -> QUESTIONING: After normal response
8. QUESTIONING -> EVALUATING: Only when student explicitly requests to end the exam (e.g., "I want to end the exam", "I'm finished", "END_EXAM", "Let's proceed to evaluation"). Do NOT transition to EVALUATING state unless student clearly expresses desire to end exam.
9. EVALUATING -> COMPLETED: Only after evaluation is complete

For QUESTIONING state:
- Stay in QUESTIONING if the answer is relevant and not requesting to end
- Move to EXPLAINING if student shows confusion
- Move to CHAT if student gives meaningless answers
- Move to EVALUATING only if student explicitly requests to end exam

For EVALUATING state:
- Determine if ready for final evaluation
- If ready, proceed with evaluation and move to COMPLETED
- If not ready, stay in current state"""

        # Call GPT with the state-specific function
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": answer},
            ],
            functions=[function_def],
            function_call="auto",
        )

        result = json.loads(response.choices[0].message.function_call.arguments)
        print(f"GPT response result: {result}")

        # 如果是 EVALUATING 状态且准备好进行评估
        if current_state == ExamState.EVALUATING and result.get("ready_for_evaluation"):
            evaluation_result = self.handle_evaluating_state()
            if evaluation_result:
                result["evaluation"] = evaluation_result.dict()
                result["type"] = "evaluation"
                result["content"] = "考试已结束，正在生成评估报告..."

        return result

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

    async def _generate_final_evaluation(self) -> Dict:
        """Generate final evaluation report"""
        # 生成最终评估
        await self.evaluation_service.generate_final_evaluation()

        # 获取评估结果
        evaluation = self.evaluation_service.get_final_evaluation()

        return {
            "total_score": evaluation.total_score,
            "final_score": evaluation.final_score,
            "final_level": evaluation.final_level,
            "final_feedback": evaluation.final_feedback,
            "question_evaluations": {
                qid: {
                    "question": eval.question,
                    "metrics": eval.metrics.dict(),
                    "feedback": eval.feedback,
                    "difficulty": eval.difficulty,
                    "time_taken": eval.time_taken,
                    "level": eval.level,
                    "raw_response": eval.raw_response,
                }
                for qid, eval in evaluation.question_evaluations.items()
            },
            "topic_coverage": evaluation.topic_coverage,
            "behavior_score": evaluation.behavior_score,
        }

    def get_progress_evaluation(self) -> Dict:
        """获取当前进度评估"""
        current_state = self.state_machine.get_current_state()

        # 基础统计信息
        stats = {
            "questions_answered": self.session_metrics["questions_answered"],
            "hints_requested": self.session_metrics["hints_requested"],
            "current_difficulty": self.state_machine.context.get("current_difficulty", 3),
            "current_state": current_state,  # 直接使用状态字符串
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

        # 获取所有评估结果
        recent_evaluations = []
        for qid, eval in self.evaluation_service.current_evaluation.question_evaluations.items():
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

    def should_end_exam(self) -> bool:
        # 1. 时间限制
        total_time = time.time() - self.exam_start_time
        if total_time > MAX_EXAM_DURATION:
            return True

        # 2. 问题完成度
        if not self.state_machine.get_current_question():
            return True

        # 3. 学生表现
        evaluations = self.evaluation_service.get_final_evaluation()
        avg_score = evaluations.total_score

        # 如果学生表现特别好（比如平均分超过90），可以提前结束
        if avg_score > 90 and self.session_metrics["questions_answered"] >= MIN_QUESTIONS:
            return True

        return False

    def get_question_evaluation(self, question_id: str) -> Dict:
        """获取特定问题的评估结果"""
        if not self.evaluation_service.current_evaluation.question_evaluations:
            return {"error": "No evaluations found"}

        eval = self.evaluation_service.current_evaluation.question_evaluations.get(question_id)
        if not eval:
            return {"error": f"No evaluation found for question {question_id}"}

        return {
            "question_id": question_id,
            "score": {
                "accuracy": eval.metrics.accuracy,
                "clarity": eval.metrics.clarity,
                "understanding": eval.metrics.understanding,
            },
            "feedback": eval.feedback,
            "time_taken": eval.time_taken,
        }

    def handle_evaluating_state(self):
        """处理评估状态"""
        print(f"HANDLE EVALUATING STATE")
        print(f"Current topic: {self.current_topic}")  # 添加日志
        if self.state_machine.current_state in ["EVALUATING", "COMPLETED"]:
            print("考试已结束，正在获取评估报告...")

            # 生成并保存考试记录
            exam_record = ExamRecord.create_from_exam_session(self)
            exam_record.save_to_file()

            # 获取最终评估报告
            return self.evaluation_service.get_final_evaluation()
        return None

    async def _generate_chat_response(self, user_input: str) -> str:
        """使用对话历史生成聊天响应"""
        print(f"\n=== 生成聊天响应 ===")
        print(f"用户输入: {user_input}")

        # 构建包含对话历史的消息列表
        system_prompt = """You are a professor conducting an oral exam, currently engaging in face-to-face communication with a student.

Please adhere to the following guidelines:
1. Maintain a professional and friendly demeanor, interacting with the student as a real professor would.
2. If the student asks questions related to the exam topic, provide educational responses without directly giving away answers.
3. If the student shows signs of fatigue or distraction (e.g., "I need water," "I want to sleep"), express understanding but appropriately encourage them to continue the exam.
4. If the student wishes to resume the formal exam, inform them that you can return to exam mode at any time.
5. Responses should be concise and direct, fitting the conversational style of an oral exam setting.
6. Ensure continuity in the conversation by referencing previous exchanges.

Your responses should resemble immediate reactions in an exam setting, combining the professionalism of a professor with appropriate human empathy.
"""

        # 创建消息列表，包含完整对话历史
        messages = [{"role": "system", "content": system_prompt}]

        # 添加最近的对话历史（确保对话上下文完整）
        if self.conversation_history:
            # 排除最后一条用户消息，因为我们会单独添加它
            history_to_use = (
                self.conversation_history[:-1]
                if self.conversation_history[-1]["role"] == "user"
                else self.conversation_history
            )
            messages.extend(history_to_use)

        # 添加当前用户输入
        messages.append({"role": "user", "content": user_input})

        print(f"使用对话历史生成回复，历史记录数: {len(messages)-1}")

        # 调用OpenAI API生成响应
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
        )

        chat_response = response.choices[0].message.content.strip()

        # 将生成的回复添加到对话历史
        self._add_to_conversation_history("assistant", chat_response)

        return chat_response

    async def process_chat_answer(self, answer: str) -> Dict:
        """处理CHAT状态下的学生回答"""
        print(f"\n=== 处理CHAT状态回答 ===")
        current_state = self.state_machine.get_current_state()

        # 安全检查：确保当前是CHAT状态
        if current_state != ExamState.CHAT:
            return {"error": "当前不是CHAT状态"}

        # 添加用户消息到对话历史
        self._add_to_conversation_history("user", answer)

        try:
            # 检测学生是否想要返回正常考试
            state_result = await self.detect_state(answer, current_state)
            print(f"状态检测结果: {state_result}")

            # 如果学生想要返回到正常考试状态
            if state_result.get("wants_to_return", False):
                return_state = state_result.get("return_state")
                if not return_state:
                    return_state = self.state_machine.context.get(
                        "previous_state", ExamState.QUESTIONING
                    )
                print(f"从CHAT状态返回到: {return_state}")
                self.state_machine.transition(ExamState(return_state))
                return self.get_next_interaction()

            # 否则，生成一个聊天响应
            chat_response = await self._generate_chat_response(answer)
            return {"type": "chat", "content": chat_response}

        except Exception as e:
            print(f"处理CHAT回答时出错: {str(e)}")
            # 出错时尝试直接生成聊天响应，不进行状态检测
            try:
                chat_response = await self._generate_chat_response(answer)
                return {"type": "chat", "content": chat_response}
            except:
                # 如果仍然失败，返回一个通用回复
                return {
                    "type": "chat",
                    "content": "抱歉，我现在无法处理您的请求。您可以尝试继续考试或者问一个不同的问题。",
                }
