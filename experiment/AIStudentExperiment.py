import asyncio
import json
import os
import statistics
import time
from datetime import datetime

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import seaborn as sns
from dotenv import load_dotenv
from openai import OpenAI

# 加载环境变量
load_dotenv()

# 设置matplotlib中文支持
plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans", "Arial Unicode MS", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False


class AIStudent:
    """AI学生模型，根据不同类型生成不同质量的答案"""

    def __init__(self, level: str):
        self.level = level
        self.config = {
            "Excellent": {
                "knowledge_coverage": 0.9,
                "context_usage": 1.0,
                "hint_probability": 0.1,
                "incorrect_context_ratio": 0.0,
                "system_prompt": """You are now acting as an exceptionally excellent student taking an oral exam on reinforcement learning and optimal control theory.

1. You have thoroughly studied the subject and demonstrate deep understanding, but you cannot refer to any materials during the exam.
2. Your responses must be entirely verbal - avoid using mathematical formulas directly. Your answers should be clear, well-organized, and show logical understanding.
3. Demonstrate confidence and composure. When faced with open-ended questions, expand your explanation appropriately to show your understanding.
4. Keep your answers concise (100-150 words) and conversational, as if speaking in a real oral exam. Don't list points or use bullet points.
5. Show depth of knowledge but in natural speech patterns with occasional pauses or verbal fillers (like "well", "so", "you see").

Remember to answer as an excellent student would in an oral exam - knowledgeable, articulate, but still speaking naturally without excessive formality.""",
            },
            "Average": {
                "knowledge_coverage": 0.7,
                "context_usage": 0.5,
                "hint_probability": 0.3,
                "incorrect_context_ratio": 0.2,
                "system_prompt": """You are now acting as an average student with a basic grasp of reinforcement learning and optimal control theory, taking an oral exam.

1. You have studied the material but your understanding is incomplete in several areas. You cannot refer to any materials during the exam.
2. Your responses must be entirely verbal - avoid using mathematical formulas. Your answers are somewhat organized but lack depth or precision.
3. Show moderate confidence with occasional uncertainty. You sometimes hesitate and may struggle with more complex concepts.
4. Keep your answers brief (80-120 words) and conversational. Use natural language with some verbal fillers (like "um", "I think", "maybe").
5. Your explanations should be partially correct but contain minor misunderstandings or gaps.

Remember to answer as an average student would in an oral exam - somewhat knowledgeable but showing some confusion, speaking in a natural way with some hesitation when unsure.""",
            },
            "Poor": {
                "knowledge_coverage": 0.4,
                "context_usage": 0.1,
                "hint_probability": 0.6,
                "incorrect_context_ratio": 0.6,
                "system_prompt": """You are now acting as a student with severely flawed knowledge of reinforcement learning and optimal control theory, taking an oral exam.

1. You have completely misunderstood the core material and developed an incorrect knowledge framework. You cannot refer to any materials during the exam.
2. Your responses must be entirely verbal - avoid using mathematical formulas. Your answers contain seriously flawed content with confused logic.
3. Display unreasonable confidence in your incorrect answers despite your misunderstandings.
4. Keep your answers short (50-100 words) and conversational. Use many verbal fillers (like "um", "you know", "basically") and speak in a natural, disorganized way.
5. Make systematic errors - apply concept A's definition to concept B, reverse steps in algorithms, or claim techniques have effects opposite to their actual effects.

Remember to answer as a poor student would in an oral exam - confidently incorrect, speaking naturally but with confused understanding, without simply saying you don't know.""",
            },
        }[level]

        # 加载问题数据
        self.questions_data = self.load_questions_data()

        # 初始化OpenAI客户端
        self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def load_questions_data(self):
        """加载问题和上下文数据"""
        try:
            # 首先尝试直接加载已知的绝对路径
            absolute_path = "/home/zhc/chatexaminer/data/exam_questions.json"
            if os.path.exists(absolute_path):
                print(f"Loading questions data from: {absolute_path}")
                with open(absolute_path, "r", encoding="utf-8") as f:
                    return json.load(f)

            # 尝试相对路径
            questions_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "data", "exam_questions.json"
            )
            if not os.path.exists(questions_path):
                print(f"Warning: Questions data file not found at {questions_path}")
                # 尝试在其他可能的位置查找文件
                alternate_paths = [
                    "data/exam_questions.json",
                    "../data/exam_questions.json",
                    "exam_questions.json",
                    os.path.join(os.getcwd(), "data", "exam_questions.json"),
                ]

                for path in alternate_paths:
                    if os.path.exists(path):
                        questions_path = path
                        print(f"Found questions data at: {questions_path}")
                        break
                else:
                    print(
                        "Could not find questions data file. Context enhancement will be disabled."
                    )
                    return {}

            print(f"Loading questions data from: {questions_path}")
            with open(questions_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(f"Successfully loaded {len(data)} questions")
                return data
        except Exception as e:
            print(f"Error loading questions data: {str(e)}")
            return {}

    def _get_context_for_question(self, question_id):
        """根据question_id获取相应的context"""
        if not question_id or not self.questions_data:
            print(f"无法获取上下文：question_id为空或无问题数据")
            return None

        print(f"正在为问题ID '{question_id}' 查找上下文...")

        # 尝试直接匹配问题ID
        question_data = self.questions_data.get(question_id)

        # 如果没有找到，尝试不区分大小写匹配
        if not question_data:
            for q_id, q_data in self.questions_data.items():
                if q_id.lower() == question_id.lower():
                    question_data = q_data
                    print(f"通过不区分大小写匹配找到问题: {q_id}")
                    break

        # 如果仍然没有找到，尝试在问题ID或问题文本中查找
        if not question_data:
            print(f"未能直接匹配问题ID '{question_id}'，尝试部分匹配...")
            for q_id, q_data in self.questions_data.items():
                # 检查问题ID是否包含在当前ID中
                if question_id in q_id or q_id in question_id:
                    question_data = q_data
                    print(f"通过部分ID匹配找到问题: {q_id}")
                    break
                # 检查问题文本中是否包含ID
                elif "question" in q_data and question_id in q_data["question"]:
                    question_data = q_data
                    print(f"通过问题文本匹配找到问题: {q_id}")
                    break

        if question_data and "context" in question_data:
            print(f"找到问题上下文，长度: {len(question_data['context'])}")
            # 根据学生类型决定使用多少context
            context = question_data["context"]

            if self.level == "Excellent":
                # 优秀学生获得完整context，并做好充分准备
                print(f"优秀学生获取完整上下文")
                full_context = "\n".join(context)
                return full_context
            elif self.level == "Average":
                # 中等学生获得部分context
                coverage = self.config["context_usage"]
                context_length = max(1, int(len(context) * coverage))
                print(f"中等学生获取部分上下文 ({context_length}/{len(context)})")
                return "\n".join(context[:context_length])
            else:
                # 较差学生获得更少的context，可能还有错误信息
                coverage = self.config["context_usage"]
                incorrect_ratio = self.config["incorrect_context_ratio"]

                context_length = max(1, int(len(context) * coverage))
                selected_context = context[:context_length]
                print(f"较差学生获取有限上下文 ({context_length}/{len(context)})")

                # 如果有错误context比例，可以添加一些误导信息
                if incorrect_ratio > 0 and len(selected_context) > 0:
                    # 这里简单实现，实际应用中可能需要更复杂的错误生成逻辑
                    incorrect_info = "Note that this approach is completely opposite to what most textbooks teach, and contradicts conventional wisdom in the field."
                    selected_context.append(incorrect_info)
                    print("为较差学生添加了误导信息")

                return "\n".join(selected_context)
        else:
            print(f"未找到问题 '{question_id}' 的上下文")

        return None

    def generate_answer(self, question_text, context=None, question_id=None):
        """根据学生类型生成答案"""
        try:
            # 根据学生类型设置不同的max_tokens
            max_tokens = {
                "Excellent": 250,  # 约150词
                "Average": 200,  # 约120词
                "Poor": 150,  # 约100词
            }.get(self.level, 200)

            print(f"{self.level}类型学生开始生成答案，问题ID: {question_id or '未提供'}")

            # 如果提供了question_id，获取相应的context
            question_context = context
            context_source = "外部提供"

            if question_id:
                question_context_from_id = self._get_context_for_question(question_id)
                if question_context_from_id:
                    context_source = f"问题ID {question_id}"
                    if context:  # 如果同时提供了外部context和从ID获取的context，合并两者
                        question_context = f"{context}\n\n{question_context_from_id}"
                        context_source = f"外部提供+问题ID {question_id}"
                    else:
                        question_context = question_context_from_id
            elif context:
                question_context = context

            if question_context:
                print(
                    f"使用来源于{context_source}的上下文，长度：{len(question_context.split())}字"
                )
            else:
                print(f"无可用上下文，将根据基础知识回答")

            # 调用OpenAI API生成回答
            messages = [{"role": "system", "content": self.config["system_prompt"]}]

            user_content = f"Question: {question_text}"
            if question_context:
                if self.level == "Excellent":
                    # 优秀学生更好地整合上下文信息到回答中
                    user_content += f"\n\nYou have thoroughly studied this topic and remember the following information that is relevant to this question: {question_context}"
                else:
                    user_content += (
                        f"\n\nRelevant information from your studies: {question_context}"
                    )

            messages.append({"role": "user", "content": user_content})

            print(f"正在调用AI模型生成回答...")
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini", messages=messages, temperature=0.7, max_tokens=max_tokens
            )

            answer = response.choices[0].message.content
            print(f"成功生成回答，长度：{len(answer.split())}字")
            return answer

        except Exception as e:
            print(f"生成回答时出错: {str(e)}")
            # 返回英文备用答案，根据学生类型有明显区别
            if self.level == "Excellent":
                return "Well, direct methods for optimal control are really powerful because they transform continuous problems into discrete ones we can solve numerically. What makes them different from indirect methods is that we don't need to derive those complex necessary conditions. I find them particularly useful for problems with constraints because the implementation is more straightforward. You see, with direct methods like collocation, we can handle various constraints naturally within the optimization framework."
            elif self.level == "Average":
                return "Um, direct methods in optimal control are basically ways to convert the continuous problem into something we can solve with computers. I think they're different from indirect methods because... well, they don't use those complicated equations with co-states, which makes them easier to use. They work pretty well for problems with constraints, I believe. I'm not entirely sure, but I think direct shooting and collocation are the main techniques people use."
            else:
                return "So, direct methods are like, you know, when you solve the control problem directly? I'm pretty sure they're better than indirect methods because they're more... direct, obviously. You basically just guess the solution and see if it works. I think you need to use Newton's method for this, and it's related to Euler's method somehow. The main advantage is that they're faster and you don't need to understand all that complicated math stuff."


class ExamAPIClient:
    """ChatExaminer API客户端"""

    def __init__(self, base_url="http://localhost:8000/api/exam"):
        self.base_url = base_url
        self.session_id = None
        self.headers = {"Content-Type": "application/json"}

    def start_exam(self, topic, max_retries=3, retry_delay=2):
        """开始一个新考试会话，带重试机制"""
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/start",
                    json={"topic": topic},
                    headers=self.headers,
                    timeout=15,  # 增加超时时间
                )
                data = response.json()
                self.session_id = data["data"]["session_id"]
                return data
            except requests.exceptions.ConnectionError as e:
                print(f"Connection error (attempt {attempt+1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise
            except Exception as e:
                print(f"Unexpected error: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise

    def submit_answer(self, answer, max_retries=3, retry_delay=2):
        """提交答案，带重试机制"""
        if not self.session_id:
            raise ValueError("No active session. Call start_exam first.")

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/{self.session_id}/answer",
                    json={"answer": answer},
                    headers=self.headers,
                    timeout=15,
                )
                return response.json()
            except requests.exceptions.ConnectionError as e:
                print(f"Connection error (attempt {attempt+1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise
            except Exception as e:
                print(f"Unexpected error: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise

    def get_state(self, max_retries=3, retry_delay=2):
        """获取考试状态，带重试机制"""
        if not self.session_id:
            raise ValueError("No active session. Call start_exam first.")

        for attempt in range(max_retries):
            try:
                response = requests.get(
                    f"{self.base_url}/{self.session_id}/state", headers=self.headers, timeout=15
                )
                return response.json()
            except requests.exceptions.ConnectionError as e:
                print(f"Connection error (attempt {attempt+1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise
            except Exception as e:
                print(f"Unexpected error: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise

    def get_evaluation(self, max_retries=3, retry_delay=2):
        """获取最终评估结果，带重试机制"""
        if not self.session_id:
            raise ValueError("No active session. Call start_exam first.")

        for attempt in range(max_retries):
            try:
                response = requests.get(
                    f"{self.base_url}/{self.session_id}/evaluation",
                    headers=self.headers,
                    timeout=15,
                )
                return response.json()
            except requests.exceptions.ConnectionError as e:
                print(f"Connection error (attempt {attempt+1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise
            except Exception as e:
                print(f"Unexpected error: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise


class ExperimentRunner:
    """实验控制器"""

    def __init__(self, output_dir="experiment/AI_Student_Experiment_Results"):
        self.api_client = ExamAPIClient()
        self.output_dir = output_dir
        self.results = {"Excellent": [], "Average": [], "Poor": []}

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

    def run_experiment(
        self,
        student_types=["Excellent", "Average", "Poor"],
        topic="Direct Methods for Optimal Control",
        num_questions=7,
        tests_per_type=3,
    ):
        """运行完整实验"""
        print(f"Starting experiment - Topic: {topic}, Tests per student type: {tests_per_type}")

        for student_type in student_types:
            print(f"\n===== Testing student type: {student_type} =====")

            for test_num in range(1, tests_per_type + 1):
                print(f"\n----- Test #{test_num} -----")

                # 创建AI学生
                student = AIStudent(student_type)

                # 记录本次测试
                test_record = {
                    "test_id": f"{student_type}_test_{test_num}",
                    "student_type": student_type,
                    "topic": topic,
                    "timestamp": datetime.now().isoformat(),
                    "questions": [],
                    "evaluation": None,
                }

                try:
                    # 创建新的API客户端以避免会话状态混淆
                    self.api_client = ExamAPIClient()

                    # 开始考试
                    print("Starting exam session...")
                    start_data = self.api_client.start_exam(topic)
                    test_record["session_id"] = self.api_client.session_id

                    # 发送确认信息开始考试 - 第一个问题来自于这个响应
                    print("Sending confirmation to start the exam...")
                    confirmation_response = self.api_client.submit_answer("yes")
                    time.sleep(2)  # 给服务器一些时间处理
                    print(
                        f"Confirmation response state: {confirmation_response.get('state', 'unknown')}"
                    )

                    # 获取第一个问题 - 直接从确认响应的 data.content 字段中获取
                    current_question = {}
                    if confirmation_response.get("data", {}).get("content"):
                        # 从data.content字段构建问题对象
                        content = confirmation_response["data"]["content"]
                        question_id = confirmation_response["data"].get("question_id", "Q1")
                        current_question = {"question": content, "question_id": question_id}
                        print(
                            f"Extracted first question from confirmation response: {content[:100]}..."
                        )
                    else:
                        # 如果没有找到，尝试其他可能的字段
                        if confirmation_response.get("data", {}).get("current_question"):
                            current_question = confirmation_response["data"]["current_question"]
                        else:
                            # 最后尝试从状态获取
                            print(
                                "Warning: No question found in confirmation response, trying to get from state..."
                            )
                            state_data = self.api_client.get_state()
                            if state_data.get("data", {}).get("content"):
                                content = state_data["data"]["content"]
                                question_id = state_data["data"].get("question_id", "Q1")
                                current_question = {"question": content, "question_id": question_id}
                            elif state_data.get("data", {}).get("current_question"):
                                current_question = state_data["data"]["current_question"]

                    # 打印第一个问题以进行调试
                    if current_question.get("question"):
                        print(f"First question: {current_question.get('question')[:100]}...")
                    else:
                        print(
                            f"Warning: Could not find first question! Response: {confirmation_response}"
                        )

                    # 回答问题
                    question_count = 0
                    max_questions = num_questions

                    # 修复：添加安全检查以防current_question为空
                    while question_count < max_questions and current_question:
                        q_text = current_question.get("question", "")
                        q_id = current_question.get("question_id", f"Q{question_count+1}")

                        if not q_text:
                            print(f"Warning: Empty question received. Skipping to next step.")
                            break

                        print(f"Question #{question_count+1}: {q_text[:100]}...")

                        # 生成答案
                        answer = student.generate_answer(q_text, question_id=q_id)
                        print(f"AI student answer: {answer[:100]}...")

                        # 创建问题记录并存储当前问题ID、文本和答案
                        question_record = {
                            "question_id": q_id,
                            "question_text": q_text,
                            "answer": answer,
                            "timestamp": datetime.now().isoformat(),
                        }

                        # 将问题记录添加到测试记录中
                        test_record["questions"].append(question_record)

                        # 提交答案并等待响应
                        response = self.api_client.submit_answer(answer)
                        time.sleep(1)  # 给系统一点时间处理

                        # 保存当前状态以便后续使用
                        current_state = response.get("state", "")

                        # 检查是否处于EXPLAINING状态，如果是，需要处理
                        if current_state == "EXPLAINING":
                            print(
                                "In EXPLAINING state after answer, sending COMPLETE to continue..."
                            )
                            complete_response = self.api_client.submit_answer("COMPLETE")
                            time.sleep(2)
                            current_state = complete_response.get("state", "")
                            print(f"State after COMPLETE: {current_state}")
                            # 如果有下一个问题，可能在complete_response中
                            response = complete_response

                        # 检查是否可以获取下一个问题
                        try:
                            # 从response中获取下一个问题 - 有两种可能的格式
                            next_question = None

                            # 方式1：从data.content字段获取
                            if (
                                response.get("data", {}).get("content")
                                and response.get("data", {}).get("type") == "question"
                            ):
                                content = response["data"]["content"]
                                question_id = response["data"].get(
                                    "question_id", f"Q{question_count+2}"
                                )  # 默认为下一个ID
                                next_question = {"question": content, "question_id": question_id}
                                print(
                                    f"Extracted next question from response.data.content: {content[:100]}..."
                                )

                            # 方式2：从data.current_question字段获取
                            elif response.get("data", {}).get("current_question"):
                                next_question = response["data"]["current_question"]

                            if next_question:
                                current_question = next_question
                            else:
                                # 如果response中没有问题，尝试从状态中获取
                                print("No question found in response, trying to get from state...")
                                state_data = self.api_client.get_state()

                                # 尝试两种可能的格式
                                if (
                                    state_data.get("data", {}).get("content")
                                    and state_data.get("data", {}).get("type") == "question"
                                ):
                                    content = state_data["data"]["content"]
                                    question_id = state_data["data"].get(
                                        "question_id", f"Q{question_count+2}"
                                    )
                                    current_question = {
                                        "question": content,
                                        "question_id": question_id,
                                    }
                                elif state_data.get("data", {}).get("current_question"):
                                    current_question = state_data["data"]["current_question"]
                                else:
                                    # 如果仍然没有问题，可能考试已结束
                                    if question_count < max_questions - 1:
                                        print(
                                            f"No question at count {question_count+1}. Checking state..."
                                        )
                                        if (
                                            current_state == "CHAT"
                                            or current_state == "EVALUATING"
                                            or current_state == "COMPLETED"
                                        ):
                                            print(
                                                f"In {current_state} state, continuing to end exam..."
                                            )
                                            break
                                    else:
                                        print("No more questions available.")
                                        break
                        except Exception as e:
                            print(f"Error retrieving next question: {str(e)}")
                            # 尝试从状态获取问题
                            try:
                                state_data = self.api_client.get_state()
                                current_state = state_data.get("state", "")
                                current_question = state_data.get("data", {}).get(
                                    "current_question", {}
                                )
                                if not current_question:
                                    print("No more questions available after error.")
                                    break
                            except:
                                print("Failed to recover after error. Moving to next phase.")
                                break

                        question_count += 1
                        time.sleep(1)  # 防止请求过快

                    # 确保完成了足够的问题
                    if question_count < max_questions:
                        print(
                            f"Warning: Only answered {question_count} questions out of {max_questions}"
                        )

                    # 处理考试结束流程
                    self._handle_exam_completion(test_record)

                    # 注意：_handle_exam_completion现在负责将结果添加到self.results中

                except Exception as e:
                    print(f"Error during test: {str(e)}")
                    test_record["error"] = str(e)

                # 保存中间结果
                self._save_intermediate_results(student_type, test_num, test_record)

                # 测试间等待，避免服务器过载
                time.sleep(8)  # 增加测试间隔时间

        # 保存最终结果
        self._save_final_results()

        # 分析结果
        self.analyze_results()

        return self.results

    def _handle_exam_completion(self, test_record):
        """处理考试结束阶段，获取评估结果"""
        try:
            # 获取当前状态
            state_data = self.api_client.get_state()
            current_state = state_data.get("state", "UNKNOWN")
            print(f"Current state before completion process: {current_state}")

            # 1. 处理EXPLAINING状态 - 需要先发送COMPLETE转回QUESTIONING
            if current_state == "EXPLAINING":
                print(
                    "In EXPLAINING state, sending 'COMPLETE' to return to QUESTIONING state first..."
                )
                complete_response = self.api_client.submit_answer("COMPLETE")
                print(
                    f"Response after COMPLETE from EXPLAINING: {complete_response.get('state', 'unknown')}"
                )
                time.sleep(3)

                # 重新检查状态
                state_data = self.api_client.get_state()
                current_state = state_data.get("state", "UNKNOWN")
                print(f"State after COMPLETE from EXPLAINING: {current_state}")

            # 2. 处理CHAT状态 - 需要发送return退出
            if current_state == "CHAT":
                print("In CHAT state, sending 'return' to exit CHAT state...")
                return_response = self.api_client.submit_answer("return")
                print(
                    f"Response after 'return' from CHAT: {return_response.get('state', 'unknown')}"
                )
                time.sleep(3)

                # 重新检查状态
                state_data = self.api_client.get_state()
                current_state = state_data.get("state", "UNKNOWN")
                print(f"State after 'return' from CHAT: {current_state}")

            # 反复尝试直到成功进入EVALUATING状态
            max_attempts = 5
            for attempt in range(max_attempts):
                # 发送END_EXAM进入评估状态
                print(
                    f"Sending END_EXAM to enter evaluation state (attempt {attempt+1}/{max_attempts})..."
                )
                end_response = self.api_client.submit_answer("END_EXAM")
                print(f"Response state after END_EXAM: {end_response.get('state', 'unknown')}")

                # 等待状态转换完成
                time.sleep(3)

                # 检查当前状态
                state_data = self.api_client.get_state()
                current_state = state_data.get("state", "UNKNOWN")
                print(f"Current state after END_EXAM: {current_state}")

                # 如果已经进入EVALUATING状态，退出循环
                if current_state == "EVALUATING":
                    print("Successfully entered EVALUATING state")
                    break

                # 如果仍然是EXPLAINING状态，需要先发送COMPLETE
                if current_state == "EXPLAINING":
                    print("Still in EXPLAINING state, sending COMPLETE first...")
                    self.api_client.submit_answer("COMPLETE")
                    time.sleep(3)
                    continue

                # 如果仍然不在EVALUATING状态，休息一会再试
                print(f"Not in EVALUATING state yet, waiting... (current state: {current_state})")
                time.sleep(3)

            # 发送COMPLETE完成考试
            print("Sending COMPLETE to complete the exam...")
            complete_response = self.api_client.submit_answer("COMPLETE")
            print(f"Response state after COMPLETE: {complete_response.get('state', 'unknown')}")

            # 等待评估完成 - 增加等待时间
            time.sleep(5)

            # 尝试获取评估结果
            print("Getting evaluation results...")
            for retry in range(10):  # 增加重试次数
                try:
                    evaluation = self.api_client.get_evaluation()
                    if evaluation.get("data") and "total_score" in evaluation.get("data", {}):
                        test_record["evaluation"] = evaluation
                        # 打印评估摘要
                        total_score = evaluation["data"].get("total_score", 0)
                        final_level = evaluation["data"].get("final_level", "Unknown")
                        print(f"Total score: {total_score}, Final level: {final_level}")

                        # 直接打印评估数据，以帮助调试
                        print(f"Evaluation data retrieved and saved successfully")

                        # 检查已回答问题数量是否达到最低要求(5个)
                        if len(test_record["questions"]) >= 5:
                            # 保存该评估数据到测试记录中
                            self.results[test_record["student_type"]].append(test_record)
                            print(
                                f"Added test record to results (questions: {len(test_record['questions'])})"
                            )
                        else:
                            print(
                                f"Warning: Test record has fewer than 5 questions ({len(test_record['questions'])}), not including in statistics"
                            )
                        break
                    else:
                        print(f"Evaluation not ready yet, waiting... (attempt {retry+1}/10)")
                        # 如果重试次数超过一半，尝试发送COMPLETE再次激活评估
                        if retry >= 3 and retry % 2 == 1:
                            print("Sending COMPLETE again to trigger evaluation...")
                            self.api_client.submit_answer("COMPLETE")
                except Exception as e:
                    print(f"Error during evaluation retrieval: {str(e)}")

                time.sleep(3 + retry)  # 渐进增加等待时间

            if not test_record.get("evaluation"):
                print("Warning: No valid evaluation data received.")

                # 尝试获取进度评估
                try:
                    print("Trying to get progress evaluation instead...")
                    progress = self.api_client.get_state()
                    if progress.get("data") and "context" in progress.get("data", {}):
                        context = progress["data"]["context"]
                        print(f"Progress context: {context}")
                        test_record["progress_context"] = context

                        # 仍然添加到结果中，即使没有完整评估
                        # 只有当问题数量达到最低要求(5个)时才添加
                        if len(test_record["questions"]) >= 5:
                            self.results[test_record["student_type"]].append(test_record)
                            print(
                                f"Added test record with progress context (questions: {len(test_record['questions'])})"
                            )
                        else:
                            print(
                                f"Warning: Test record has fewer than 5 questions ({len(test_record['questions'])}), not including in statistics"
                            )
                except Exception as e:
                    print(f"Error getting progress data: {str(e)}")

        except Exception as e:
            print(f"Error during exam completion: {str(e)}")

    def _save_intermediate_results(self, student_type, test_num, test_record):
        """保存中间测试结果"""
        result_file = os.path.join(
            self.output_dir,
            f"{student_type}_test_{test_num}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )

        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(test_record, f, ensure_ascii=False, indent=2)

        print(f"Test results saved to: {result_file}")

    def _save_final_results(self):
        """保存最终实验结果"""
        result_file = os.path.join(
            self.output_dir, f"experiment_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print(f"Final experiment results saved to: {result_file}")

    def analyze_results(self):
        """分析实验结果"""
        print("\n===== Experiment Results Analysis =====")

        # 汇总信息
        print("\n----- Summary of Experiment Results -----")
        total_tests = 0
        valid_tests = 0

        for student_type, tests in self.results.items():
            type_total = len(tests)
            type_valid = len([t for t in tests if len(t.get("questions", [])) >= 5])
            total_tests += type_total
            valid_tests += type_valid
            print(
                f"{student_type} student: {type_valid}/{type_total} valid tests (with ≥5 questions)"
            )

        print(f"Total: {valid_tests}/{total_tests} valid tests included in statistics")
        print("--------------------------------------\n")

        # 提取评估分数
        scores = {}
        for student_type, tests in self.results.items():
            scores[student_type] = []
            print(f"Processing {len(tests)} tests for student type: {student_type}")

            for test in tests:
                # 只有当问题数量达到最低要求时才包含在统计中
                if len(test.get("questions", [])) < 5:
                    print(f"  - Skipping test with only {len(test.get('questions', []))} questions")
                    continue

                if test.get("evaluation") and "data" in test["evaluation"]:
                    total_score = test["evaluation"]["data"].get("total_score", 0)
                    scores[student_type].append(total_score)
                    print(f"  - Found score: {total_score}")
                else:
                    print(f"  - Test without valid evaluation data")

            # 计算平均分和标准差
            if scores[student_type]:
                avg = sum(scores[student_type]) / len(scores[student_type])
                std = statistics.stdev(scores[student_type]) if len(scores[student_type]) > 1 else 0
                print(f"{student_type} student average score: {avg:.2f} ± {std:.2f}")
            else:
                print(f"{student_type} student: No valid evaluation data")

        # 生成分析图表
        self._generate_visualizations(scores)

    def _generate_visualizations(self, scores):
        """生成可视化图表"""
        # 修复：即使不是所有学生类型都有数据，也要生成可视化
        valid_data = False
        for student_scores in scores.values():
            if student_scores:
                valid_data = True
                break

        if not valid_data:
            print("Insufficient data to generate visualizations")
            return

        # 提取final_score和final_level数据
        final_scores = {}
        final_levels = {}
        level_mapping = {"Excellent": 1.0, "Good": 0.5, "Fair": 0, "Poor": -0.5}

        for student_type, tests in self.results.items():
            final_scores[student_type] = []
            final_levels[student_type] = []

            for test in tests:
                # 只有当问题数量达到最低要求时才包含在统计中
                if len(test.get("questions", [])) < 5:
                    continue

                if test.get("evaluation") and "data" in test["evaluation"]:
                    eval_data = test["evaluation"]["data"]

                    # 提取final_score
                    if "final_score" in eval_data:
                        final_scores[student_type].append(eval_data["final_score"])
                    # 尝试其他可能的字段名
                    elif "finalScore" in eval_data:
                        final_scores[student_type].append(eval_data["finalScore"])
                    elif "final_result" in eval_data:
                        final_scores[student_type].append(eval_data["final_result"])
                    elif "score" in eval_data:
                        final_scores[student_type].append(eval_data["score"])
                    # 如果仍然没找到，尝试使用total_score作为备选
                    elif "total_score" in eval_data:
                        final_scores[student_type].append(eval_data["total_score"])

                    # 提取final_level并转换为数值
                    level_found = False
                    # 尝试不同的可能字段名
                    for field in [
                        "final_level",
                        "finalLevel",
                        "level",
                        "grade",
                        "evaluation_result",
                    ]:
                        if field in eval_data and not level_found:
                            level = eval_data[field]
                            level_found = True

                            # 处理可能的不同格式（大小写、空格等）
                            if isinstance(level, str):
                                level_key = level.strip().title()
                                if level_key in level_mapping:
                                    final_levels[student_type].append(level_mapping[level_key])
                                else:
                                    # 尝试部分匹配
                                    for k, v in level_mapping.items():
                                        if k.lower() in level.lower():
                                            final_levels[student_type].append(v)
                                            break
                                    else:
                                        print(f"未能匹配级别: {level}")
                            elif isinstance(level, (int, float)):
                                # 如果是数值，检查是否在我们的映射范围内
                                if level in level_mapping.values():
                                    final_levels[student_type].append(level)
                                else:
                                    # 尝试映射到最接近的值
                                    closest = min(
                                        level_mapping.values(), key=lambda x: abs(x - level)
                                    )
                                    final_levels[student_type].append(closest)
                                    print(f"映射数值级别 {level} 到最接近的值: {closest}")

                    # 如果未找到级别，尝试从其他信息推断
                    if not level_found and "total_score" in eval_data:
                        score = eval_data["total_score"]
                        # 基于分数区间推断级别
                        if score >= 85:
                            final_levels[student_type].append(level_mapping["Excellent"])
                        elif score >= 70:
                            final_levels[student_type].append(level_mapping["Good"])
                        elif score >= 55:
                            final_levels[student_type].append(level_mapping["Fair"])
                        else:
                            final_levels[student_type].append(level_mapping["Poor"])

        # 创建一个更大的图形，包含6个子图
        plt.figure(figsize=(20, 15))

        # 只处理有数据的学生类型
        student_types = [st for st in scores.keys() if scores[st]]
        if not student_types:
            return

        # 直接使用英文类型名称，不需要映射

        # 1. 分数对比图 (Total Score)
        plt.subplot(3, 2, 1)
        type_labels = student_types
        avg_scores = [statistics.mean(scores[st]) for st in student_types]
        std_scores = [
            statistics.stdev(scores[st]) if len(scores[st]) > 1 else 0 for st in student_types
        ]

        bars = plt.bar(type_labels, avg_scores, yerr=std_scores, capsize=5)
        plt.title("Average Scores of Different Student Types (Total Score)")
        plt.ylabel("Score")
        plt.ylim(0, 100)

        # 在柱状图上显示具体分数
        for bar, score in zip(bars, avg_scores):
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 5,
                f"{score:.1f}",
                ha="center",
                va="bottom",
            )

        # 2. 分数分布图 (Total Score)
        plt.subplot(3, 2, 2)
        data = []
        for st in student_types:
            for score in scores[st]:
                data.append({"Student Type": st, "Score": score})

        if data:
            df = pd.DataFrame(data)
            sns.violinplot(x="Student Type", y="Score", data=df)
            plt.title("Score Distribution (Total Score)")
            plt.ylim(0, 100)

        # 3. Final Score 对比图
        plt.subplot(3, 2, 3)
        final_score_types = [st for st in final_scores.keys() if final_scores[st]]

        if final_score_types:
            final_avg_scores = [statistics.mean(final_scores[st]) for st in final_score_types]
            final_std_scores = [
                statistics.stdev(final_scores[st]) if len(final_scores[st]) > 1 else 0
                for st in final_score_types
            ]

            final_bars = plt.bar(
                final_score_types,
                final_avg_scores,
                yerr=final_std_scores,
                capsize=5,
                color="orange",
            )
            plt.title("Average Final Scores of Different Student Types")
            plt.ylabel("Final Score")

            # 在柱状图上显示具体分数
            for bar, score in zip(final_bars, final_avg_scores):
                plt.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.05,
                    f"{score:.2f}",
                    ha="center",
                    va="bottom",
                )
        else:
            plt.title("No Final Score Data Available")

        # 4. Final Level 对比图
        plt.subplot(3, 2, 4)
        level_types = [st for st in final_levels.keys() if final_levels[st]]

        if level_types:
            level_avg_scores = [statistics.mean(final_levels[st]) for st in level_types]
            level_std_scores = [
                statistics.stdev(final_levels[st]) if len(final_levels[st]) > 1 else 0
                for st in level_types
            ]

            level_bars = plt.bar(
                level_types, level_avg_scores, yerr=level_std_scores, capsize=5, color="green"
            )
            plt.title("Average Final Level of Different Student Types")
            plt.ylabel("Level Score")
            plt.ylim(-0.6, 1.1)

            # 添加水平参考线和标签
            plt.axhline(y=1.0, color="r", linestyle="-", alpha=0.3)
            plt.axhline(y=0.5, color="r", linestyle="-", alpha=0.3)
            plt.axhline(y=0.0, color="r", linestyle="-", alpha=0.3)
            plt.axhline(y=-0.5, color="r", linestyle="-", alpha=0.3)

            plt.text(len(level_types) - 1, 1.0, "Excellent", ha="right", va="bottom", color="r")
            plt.text(len(level_types) - 1, 0.5, "Good", ha="right", va="bottom", color="r")
            plt.text(len(level_types) - 1, 0.0, "Fair", ha="right", va="bottom", color="r")
            plt.text(len(level_types) - 1, -0.5, "Poor", ha="right", va="bottom", color="r")

            # 在柱状图上显示具体分数
            for bar, score in zip(level_bars, level_avg_scores):
                plt.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.05,
                    f"{score:.2f}",
                    ha="center",
                    va="bottom",
                )
        else:
            plt.title("No Final Level Data Available")

        # 5. 分数散点图 (原来的第3个图)
        plt.subplot(3, 2, 5)
        for i, st in enumerate(student_types):
            x = [i] * len(scores[st])
            plt.scatter(x, scores[st], alpha=0.7)
        plt.xticks(range(len(student_types)), student_types)
        plt.title("Scatter Plot of Scores for Each Student Type")
        plt.ylabel("Score")
        plt.ylim(0, 100)

        # 6. 学生类型区分度分析 (原来的第4个图)
        plt.subplot(3, 2, 6)
        data = []
        for st in student_types:
            for score in scores[st]:
                data.append({"Student Type": st, "Score": score})

        if data:
            df = pd.DataFrame(data)
            sns.boxplot(x="Student Type", y="Score", data=df)
            plt.title("Student Type Discrimination Analysis")
            plt.ylabel("Score")
            plt.ylim(0, 100)

        # 保存图表
        plt.tight_layout()
        plt.savefig(
            os.path.join(
                self.output_dir,
                f'experiment_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png',
            )
        )
        plt.close()

        print(f"Analysis charts saved to: {self.output_dir}")

        # 额外创建一个饼图显示每种学生类型的final_level分布
        try:
            if any(final_levels.values()):  # 确保至少有一些level数据
                plt.figure(figsize=(15, 10))

                # 将饼图替换为点状图，直观显示不同学生类型的评价等级分布
                student_type_list = []
                level_values_list = []
                level_labels_list = []

                # 收集所有数据点
                for student_type in self.results.keys():
                    if student_type not in final_levels or not final_levels[student_type]:
                        continue

                    for level_value in final_levels[student_type]:
                        student_type_list.append(student_type)
                        level_values_list.append(level_value)

                        # 为每个点添加标签
                        if level_value == 1.0:
                            level_labels_list.append("Excellent")
                        elif level_value == 0.5:
                            level_labels_list.append("Good")
                        elif level_value == 0.0:
                            level_labels_list.append("Fair")
                        elif level_value == -0.5:
                            level_labels_list.append("Poor")
                        else:
                            level_labels_list.append("Unknown")

                # 为点状图创建数据框
                level_data = pd.DataFrame(
                    {
                        "Student Type": student_type_list,
                        "Level Value": level_values_list,
                        "Level": level_labels_list,
                    }
                )

                # 不同level对应不同颜色
                colors = {
                    "Excellent": "#66b3ff",
                    "Good": "#99ff99",
                    "Fair": "#ffcc99",
                    "Poor": "#ff9999",
                }

                # 绘制点状图
                plt.figure(figsize=(12, 8))

                # 对点进行轻微抖动，使重叠点可见
                for level, color in colors.items():
                    mask = level_data["Level"] == level
                    if any(mask):
                        # 为x坐标添加小的随机抖动，使重叠的点可见
                        x_jittered = [
                            student_type + np.random.normal(0, 0.05)
                            for student_type in level_data.loc[mask, "Student Type"]
                        ]

                        plt.scatter(
                            x=x_jittered,
                            y=level_data.loc[mask, "Level Value"],
                            color=color,
                            label=level,
                            s=100,  # 点的大小
                            alpha=0.7,  # 透明度
                            edgecolors="black",  # 点的边缘颜色
                            linewidth=1,  # 边缘线宽
                        )

                # 添加水平参考线和标签
                plt.axhline(y=1.0, color="#66b3ff", linestyle="-", alpha=0.3)
                plt.axhline(y=0.5, color="#99ff99", linestyle="-", alpha=0.3)
                plt.axhline(y=0.0, color="#ffcc99", linestyle="-", alpha=0.3)
                plt.axhline(y=-0.5, color="#ff9999", linestyle="-", alpha=0.3)

                plt.text(-0.2, 1.0, "Excellent", ha="right", va="center", color="#66b3ff")
                plt.text(-0.2, 0.5, "Good", ha="right", va="center", color="#99ff99")
                plt.text(-0.2, 0.0, "Fair", ha="right", va="center", color="#ffcc99")
                plt.text(-0.2, -0.5, "Poor", ha="right", va="center", color="#ff9999")

                # 设置y轴范围和标签
                plt.ylim(-0.7, 1.2)
                plt.ylabel("Final Level")
                plt.xlabel("Student Type")
                plt.title("Distribution of Final Levels for Different Student Types")
                plt.legend()
                plt.grid(True, alpha=0.3)

                # 保存点状图
                plt.tight_layout()
                plt.savefig(
                    os.path.join(
                        self.output_dir,
                        f'level_distribution_scatter_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png',
                    )
                )
                plt.close()
                print("Level distribution scatter plot saved")
        except Exception as e:
            print(f"Error generating level distribution chart: {str(e)}")

        # 尝试生成多维度能力雷达图，如果有足够数据
        try:
            self._generate_radar_chart()
        except Exception as e:
            print(f"Error generating radar chart: {str(e)}")

    def _generate_radar_chart(self):
        """生成多维度能力雷达图"""
        # 提取不同维度的评分 - 移除Answer Completeness，只保留三个维度
        dimensions = {"Accuracy": {}, "Clarity": {}, "Understanding": {}}

        valid_dimensions = False
        student_types_with_data = set()

        # 先为所有学生类型初始化空列表
        for student_type in self.results.keys():
            for dimension in dimensions:
                dimensions[dimension][student_type] = []

        # 从评估结果中提取数据
        for student_type, tests in self.results.items():
            has_data = False

            for test in tests:
                # 检查问题数量是否达到最低要求
                if len(test.get("questions", [])) < 5:
                    continue

                # 安全检查，确保评估数据存在
                if not test.get("evaluation") or "data" not in test["evaluation"]:
                    continue

                try:
                    eval_data = test["evaluation"]["data"]

                    # 提取问题评估
                    question_evals = eval_data.get("question_evaluations", {})
                    if not question_evals:
                        print(f"No question evaluations found for {student_type}")
                        continue

                    for q_id, q_eval in question_evals.items():
                        # 跳过非字典类型的评估数据
                        if not isinstance(q_eval, dict):
                            continue

                        # 尝试从不同可能的位置提取metrics
                        metrics = None
                        if "metrics" in q_eval and isinstance(q_eval["metrics"], dict):
                            metrics = q_eval["metrics"]
                        elif "details" in q_eval and isinstance(q_eval["details"], dict):
                            metrics = q_eval["details"]

                        if metrics:
                            # 处理不同格式的数值 (数字或"90/100"格式)
                            for metric_name, metric_value in metrics.items():
                                try:
                                    dimension_key = None
                                    # 映射指标名称到维度
                                    metric_name_lower = metric_name.lower()
                                    if "准确" in metric_name or "accuracy" in metric_name_lower:
                                        dimension_key = "Accuracy"
                                    elif "清晰" in metric_name or "clarity" in metric_name_lower:
                                        dimension_key = "Clarity"
                                    elif (
                                        "理解" in metric_name
                                        or "understanding" in metric_name_lower
                                    ):
                                        dimension_key = "Understanding"

                                    if dimension_key and metric_value is not None:
                                        # 转换为浮点数
                                        if isinstance(metric_value, (int, float)):
                                            value = float(metric_value)
                                        elif isinstance(metric_value, str) and "/" in metric_value:
                                            value = float(metric_value.split("/")[0])
                                        else:
                                            # 尝试直接转换为浮点数
                                            value = float(metric_value)

                                        dimensions[dimension_key][student_type].append(value)
                                        has_data = True
                                        valid_dimensions = True
                                        student_types_with_data.add(student_type)
                                except (ValueError, TypeError, IndexError) as e:
                                    # 打印详细错误但继续处理
                                    print(f"Error parsing metric {metric_name}: {str(e)}")

                except Exception as e:
                    print(f"Error processing evaluation for {student_type}: {str(e)}")

        if not valid_dimensions:
            print("No valid dimension data for radar chart")
            return

        print(f"Student types with data: {student_types_with_data}")

        # 提取平均值 - 添加更多安全检查
        for dimension in dimensions:
            for student_type in self.results.keys():
                scores = dimensions[dimension].get(student_type, [])
                # 只有在有数据时才计算平均值
                if scores:
                    dimensions[dimension][student_type] = sum(scores) / len(scores)
                else:
                    # 确保每个student_type在每个dimension中都有值
                    dimensions[dimension][student_type] = 0

        # 只包含有数据的学生类型
        student_types = list(student_types_with_data)
        if not student_types:
            print("No student types with valid dimension data")
            return

        # 绘制雷达图
        labels = list(dimensions.keys())
        angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
        angles += angles[:1]  # 闭合图形

        plt.figure(figsize=(10, 8))
        ax = plt.subplot(111, polar=True)

        # 使用不同颜色区分不同学生类型
        colors = ["b", "r", "g", "c", "m", "y", "k"]

        # 为每个学生类型绘制一条线
        for i, student_type in enumerate(student_types):
            values = [dimensions[dim][student_type] for dim in labels]
            values += values[:1]  # 闭合数据

            label = student_type
            color = colors[i % len(colors)]
            ax.plot(angles, values, linewidth=2, label=label, color=color)
            ax.fill(angles, values, alpha=0.25, color=color)

        plt.xticks(angles[:-1], labels)
        ax.set_rlabel_position(0)
        plt.yticks([20, 40, 60, 80, 100], ["20", "40", "60", "80", "100"], color="grey")
        plt.ylim(0, 100)
        plt.legend(loc="upper right")
        plt.title("Ability Evaluation in Different Dimensions")

        # 保存图表
        radar_chart_filename = os.path.join(
            self.output_dir, f'radar_chart_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        )
        plt.savefig(radar_chart_filename)
        plt.close()

        print(f"Radar chart saved to: {radar_chart_filename}")

        # 如果没有太多数据，添加简单文本说明
        if sum(len(dimensions[dim][st]) for dim in dimensions for st in student_types) < 10:
            print(
                "Limited data available for radar chart. Results may not be statistically significant."
            )


def main():
    """主函数"""
    # 检查环境变量
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Please set it in the .env file or directly set the environment variable")
        return

    # 检查exam_questions.json文件是否存在
    questions_file_found = False
    for path in [
        "/home/zhc/chatexaminer/data/exam_questions.json",
        "data/exam_questions.json",
        "../data/exam_questions.json",
        "exam_questions.json",
        os.path.join(os.getcwd(), "data", "exam_questions.json"),
    ]:
        if os.path.exists(path):
            print(f"找到exam_questions.json文件: {path}")
            questions_file_found = True
            break

    if not questions_file_found:
        print("警告: 未找到exam_questions.json文件，将无法使用上下文增强功能")
        print("请确保在以下路径之一创建此文件:")
        print("  - /home/zhc/chatexaminer/data/exam_questions.json")
        print("  - data/exam_questions.json")
        print("  - exam_questions.json")

    # 配置matplotlib的中文字体支持
    try:
        # 尝试设置中文字体
        import matplotlib as mpl

        # 检查系统上的中文字体
        chinese_fonts = [
            "SimHei",
            "Microsoft YaHei",
            "STHeiti",
            "AR PL UMing CN",
            "WenQuanYi Micro Hei",
            "WenQuanYi Zen Hei",
            "Noto Sans CJK SC",
            "Noto Sans SC",
            "Source Han Sans CN",
            "Source Han Sans SC",
        ]

        font_found = False
        for font in chinese_fonts:
            try:
                mpl.font_manager.findfont(font)
                plt.rcParams["font.sans-serif"] = [font] + plt.rcParams["font.sans-serif"]
                font_found = True
                print(f"Using Chinese font: {font}")
                break
            except:
                continue

        if not font_found:
            print("Warning: No suitable Chinese font found. Using system defaults.")
            # 使用英文标签作为备选方案
            print("Will use English labels as fallback.")

        plt.rcParams["axes.unicode_minus"] = False
    except Exception as e:
        print(f"Warning: Failed to configure matplotlib for Chinese: {str(e)}")
        print("Using English labels as fallback.")

    # 创建实验运行器
    runner = ExperimentRunner()

    try:
        # 运行实验
        print("========== 开始AI学生实验 ==========")
        print("实验设置:")
        print("  - 学生类型: Excellent(优秀), Average(中等), Poor(较差)")
        print("  - 主题: Direct Methods for Optimal Control")
        print("  - 每个学生类型的测试次数: 3")
        print("  - 每次测试的问题数量: 7")
        print("========================================")

        runner.run_experiment(
            student_types=["Excellent", "Average", "Poor"],
            topic="Direct Methods for Optimal Control",
            num_questions=7,  # 统一使用7个问题，确保完整性
            tests_per_type=5,  # 根据需要调整
        )
        print("实验成功完成!")
    except Exception as e:
        print(f"实验运行出错: {str(e)}")
        # 尝试保存任何部分结果
        try:
            if hasattr(runner, "results") and runner.results:
                print("尝试保存部分结果...")
                runner._save_final_results()
                runner.analyze_results()
        except:
            print("保存部分结果失败。")


if __name__ == "__main__":
    main()
