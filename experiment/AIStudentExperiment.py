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

# Load environment variables
load_dotenv()

# Set matplotlib support for Chinese characters
plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans", "Arial Unicode MS", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False


class AIStudent:
    """AI student model, generates answers of different quality based on different types"""

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

        # Load question and context data
        self.questions_data = self.load_questions_data()

        # Initialize OpenAI client
        self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def load_questions_data(self):
        """Load question and context data"""
        try:
            # First, try to load from the known absolute path
            absolute_path = "/home/zhc/chatexaminer/data/exam_questions.json"
            if os.path.exists(absolute_path):
                print(f"Loading questions data from: {absolute_path}")
                with open(absolute_path, "r", encoding="utf-8") as f:
                    return json.load(f)

            # Try relative path
            questions_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "data", "exam_questions.json"
            )
            if not os.path.exists(questions_path):
                print(f"Warning: Questions data file not found at {questions_path}")
                # Try to find the file in other possible locations
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
        """Get corresponding context based on question_id"""
        if not question_id or not self.questions_data:
            print(f"Cannot get context: question_id is empty or no question data")
            return None

        print(f"Looking for context for question ID '{question_id}'...")

        # Try direct match for question ID
        question_data = self.questions_data.get(question_id)

        # If not found, try case-insensitive match
        if not question_data:
            for q_id, q_data in self.questions_data.items():
                if q_id.lower() == question_id.lower():
                    question_data = q_data
                    print(f"Found question through case-insensitive match: {q_id}")
                    break

        # If still not found, try to find in question ID or question text
        if not question_data:
            print(f"Could not directly match question ID '{question_id}', trying partial match...")
            for q_id, q_data in self.questions_data.items():
                # Check if question ID is contained in current ID
                if question_id in q_id or q_id in question_id:
                    question_data = q_data
                    print(f"Found question through partial ID match: {q_id}")
                    break
                # Check if question text contains ID
                elif "question" in q_data and question_id in q_data["question"]:
                    question_data = q_data
                    print(f"Found question through question text match: {q_id}")
                    break

        if question_data and "context" in question_data:
            print(f"Found question context, length: {len(question_data['context'])}")
            # Decide how much context to use based on student type
            context = question_data["context"]

            if self.level == "Excellent":
                # Excellent student gets full context and is well prepared
                print(f"Excellent student gets full context")
                full_context = "\n".join(context)
                return full_context
            elif self.level == "Average":
                # Average student gets partial context
                coverage = self.config["context_usage"]
                context_length = max(1, int(len(context) * coverage))
                print(f"Average student gets partial context ({context_length}/{len(context)})")
                return "\n".join(context[:context_length])
            else:
                # Poor student gets less context, possibly with error information
                coverage = self.config["context_usage"]
                incorrect_ratio = self.config["incorrect_context_ratio"]

                context_length = max(1, int(len(context) * coverage))
                selected_context = context[:context_length]
                print(f"Poor student gets limited context ({context_length}/{len(context)})")

                # If there's an error context ratio, can add some misleading information
                if incorrect_ratio > 0 and len(selected_context) > 0:
                    # Here's a simple implementation, actual application may require more complex error generation logic
                    incorrect_info = "Note that this approach is completely opposite to what most textbooks teach, and contradicts conventional wisdom in the field."
                    selected_context.append(incorrect_info)
                    print("Added misleading information for poor student")

                return "\n".join(selected_context)
        else:
            print(f"No context found for question '{question_id}'")

        return None

    def generate_answer(self, question_text, context=None, question_id=None):
        """Generate answer based on student type"""
        try:
            # Set different max_tokens based on student type
            max_tokens = {
                "Excellent": 250,  # About 150 words
                "Average": 200,  # About 120 words
                "Poor": 150,  # About 100 words
            }.get(self.level, 200)

            print(
                f"{self.level} type student starts generating answer, question ID: {question_id or 'Not provided'}"
            )

            # If question_id is provided, get corresponding context
            question_context = context
            context_source = "External provided"

            if question_id:
                question_context_from_id = self._get_context_for_question(question_id)
                if question_context_from_id:
                    context_source = f"Question ID {question_id}"
                    if (
                        context
                    ):  # If both external context and context from ID are provided, merge them
                        question_context = f"{context}\n\n{question_context_from_id}"
                        context_source = f"External provided+Question ID {question_id}"
                    else:
                        question_context = question_context_from_id
            elif context:
                question_context = context

            if question_context:
                print(
                    f"Using context from {context_source}, length: {len(question_context.split())} characters"
                )
            else:
                print(f"No usable context, will answer based on basic knowledge")

            # Call OpenAI API to generate answer
            messages = [{"role": "system", "content": self.config["system_prompt"]}]

            user_content = f"Question: {question_text}"
            if question_context:
                if self.level == "Excellent":
                    # Excellent student integrates context information better into answer
                    user_content += f"\n\nYou have thoroughly studied this topic and remember the following information that is relevant to this question: {question_context}"
                else:
                    user_content += (
                        f"\n\nRelevant information from your studies: {question_context}"
                    )

            messages.append({"role": "user", "content": user_content})

            print(f"Calling AI model to generate answer...")
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini", messages=messages, temperature=0.7, max_tokens=max_tokens
            )

            answer = response.choices[0].message.content
            print(f"Answer generated successfully, length: {len(answer.split())} characters")
            return answer

        except Exception as e:
            print(f"Error generating answer: {str(e)}")
            # Return English backup answer, with obvious differences based on student type
            if self.level == "Excellent":
                return "Well, direct methods for optimal control are really powerful because they transform continuous problems into discrete ones we can solve numerically. What makes them different from indirect methods is that we don't need to derive those complex necessary conditions. I find them particularly useful for problems with constraints because the implementation is more straightforward. You see, with direct methods like collocation, we can handle various constraints naturally within the optimization framework."
            elif self.level == "Average":
                return "Um, direct methods in optimal control are basically ways to convert the continuous problem into something we can solve with computers. I think they're different from indirect methods because... well, they don't use those complicated equations with co-states, which makes them easier to use. They work pretty well for problems with constraints, I believe. I'm not entirely sure, but I think direct shooting and collocation are the main techniques people use."
            else:
                return "So, direct methods are like, you know, when you solve the control problem directly? I'm pretty sure they're better than indirect methods because they're more... direct, obviously. You basically just guess the solution and see if it works. I think you need to use Newton's method for this, and it's related to Euler's method somehow. The main advantage is that they're faster and you don't need to understand all that complicated math stuff."


class ExamAPIClient:
    """ChatExaminer API client"""

    def __init__(self, base_url="http://localhost:8000/api/exam"):
        self.base_url = base_url
        self.session_id = None
        self.headers = {"Content-Type": "application/json"}

    def start_exam(self, topic, max_retries=3, retry_delay=2):
        """Start a new exam session with retry mechanism"""
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/start",
                    json={"topic": topic},
                    headers=self.headers,
                    timeout=15,  # Increase timeout time
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
        """Submit answer with retry mechanism"""
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
        """Get exam state with retry mechanism"""
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
        """Get final evaluation result with retry mechanism"""
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
    """Experiment controller"""

    def __init__(self, output_dir="experiment/AI_Student_Experiment_Results"):
        self.api_client = ExamAPIClient()
        self.output_dir = output_dir
        self.results = {"Excellent": [], "Average": [], "Poor": []}

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

    def run_experiment(
        self,
        student_types=["Excellent", "Average", "Poor"],
        topic="Direct Methods for Optimal Control",
        num_questions=7,
        tests_per_type=3,
    ):
        """Run complete experiment"""
        print(f"Starting experiment - Topic: {topic}, Tests per student type: {tests_per_type}")

        for student_type in student_types:
            print(f"\n===== Testing student type: {student_type} =====")

            for test_num in range(1, tests_per_type + 1):
                print(f"\n----- Test #{test_num} -----")

                # Create AI student
                student = AIStudent(student_type)

                # Record this test
                test_record = {
                    "test_id": f"{student_type}_test_{test_num}",
                    "student_type": student_type,
                    "topic": topic,
                    "timestamp": datetime.now().isoformat(),
                    "questions": [],
                    "evaluation": None,
                }

                try:
                    # Create new API client to avoid session state confusion
                    self.api_client = ExamAPIClient()

                    # Start exam
                    print("Starting exam session...")
                    start_data = self.api_client.start_exam(topic)
                    test_record["session_id"] = self.api_client.session_id

                    # Send confirmation to start exam - first question comes from this response
                    print("Sending confirmation to start the exam...")
                    confirmation_response = self.api_client.submit_answer("yes")
                    time.sleep(2)  # Give server some time to process
                    print(
                        f"Confirmation response state: {confirmation_response.get('state', 'unknown')}"
                    )

                    # Get first question - directly get from data.content field of confirmation response
                    current_question = {}
                    if confirmation_response.get("data", {}).get("content"):
                        # Build question object from data.content field
                        content = confirmation_response["data"]["content"]
                        question_id = confirmation_response["data"].get("question_id", "Q1")
                        current_question = {"question": content, "question_id": question_id}
                        print(
                            f"Extracted first question from confirmation response: {content[:100]}..."
                        )
                    else:
                        # If not found, try other possible fields
                        if confirmation_response.get("data", {}).get("current_question"):
                            current_question = confirmation_response["data"]["current_question"]
                        else:
                            # Last try to get from state
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

                    # Print first question for debugging
                    if current_question.get("question"):
                        print(f"First question: {current_question.get('question')[:100]}...")
                    else:
                        print(
                            f"Warning: Could not find first question! Response: {confirmation_response}"
                        )

                    # Answer question
                    question_count = 0
                    max_questions = num_questions

                    # Fix: Add safety check to prevent current_question from being empty
                    while question_count < max_questions and current_question:
                        q_text = current_question.get("question", "")
                        q_id = current_question.get("question_id", f"Q{question_count+1}")

                        if not q_text:
                            print(f"Warning: Empty question received. Skipping to next step.")
                            break

                        print(f"Question #{question_count+1}: {q_text[:100]}...")

                        # Generate answer
                        answer = student.generate_answer(q_text, question_id=q_id)
                        print(f"AI student answer: {answer[:100]}...")

                        # Create question record and store current question ID, text, and answer
                        question_record = {
                            "question_id": q_id,
                            "question_text": q_text,
                            "answer": answer,
                            "timestamp": datetime.now().isoformat(),
                        }

                        # Add question record to test record
                        test_record["questions"].append(question_record)

                        # Submit answer and wait for response
                        response = self.api_client.submit_answer(answer)
                        time.sleep(1)  # Give system some time to process

                        # Save current state for later use
                        current_state = response.get("state", "")

                        # Check if in EXPLAINING state, need to handle
                        if current_state == "EXPLAINING":
                            print(
                                "In EXPLAINING state after answer, sending COMPLETE to continue..."
                            )
                            complete_response = self.api_client.submit_answer("COMPLETE")
                            time.sleep(2)
                            current_state = complete_response.get("state", "")
                            print(f"State after COMPLETE: {current_state}")
                            # If there's a next question, it might be in complete_response
                            response = complete_response

                        # Check if next question can be retrieved
                        try:
                            # Get next question from response - there are two possible formats
                            next_question = None

                            # Method 1: Get from data.content field
                            if (
                                response.get("data", {}).get("content")
                                and response.get("data", {}).get("type") == "question"
                            ):
                                content = response["data"]["content"]
                                question_id = response["data"].get(
                                    "question_id", f"Q{question_count+2}"
                                )  # Default to next ID
                                next_question = {"question": content, "question_id": question_id}
                                print(
                                    f"Extracted next question from response.data.content: {content[:100]}..."
                                )

                            # Method 2: Get from data.current_question field
                            elif response.get("data", {}).get("current_question"):
                                next_question = response["data"]["current_question"]

                            if next_question:
                                current_question = next_question
                            else:
                                # If response has no question, try to get from state
                                print("No question found in response, trying to get from state...")
                                state_data = self.api_client.get_state()

                                # Try both possible formats
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
                                    # If still no question, exam might be over
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
                            # Try to get question from state
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
                        time.sleep(1)  # Prevent request too fast

                    # Ensure enough questions are answered
                    if question_count < max_questions:
                        print(
                            f"Warning: Only answered {question_count} questions out of {max_questions}"
                        )

                    # Handle exam completion process
                    self._handle_exam_completion(test_record)

                    # Note: _handle_exam_completion now handles adding results to self.results

                except Exception as e:
                    print(f"Error during test: {str(e)}")
                    test_record["error"] = str(e)

                # Save intermediate results
                self._save_intermediate_results(student_type, test_num, test_record)

                # Test wait, avoid server overload
                time.sleep(8)  # Increase test interval time

        # Save final results
        self._save_final_results()

        # Analyze results
        self.analyze_results()

        return self.results

    def _handle_exam_completion(self, test_record):
        """Handle exam completion process, get evaluation result"""
        try:
            # Get current state
            state_data = self.api_client.get_state()
            current_state = state_data.get("state", "UNKNOWN")
            print(f"Current state before completion process: {current_state}")

            # 1. Handle EXPLAINING state - need to send COMPLETE first to return to QUESTIONING state
            if current_state == "EXPLAINING":
                print(
                    "In EXPLAINING state, sending 'COMPLETE' to return to QUESTIONING state first..."
                )
                complete_response = self.api_client.submit_answer("COMPLETE")
                print(
                    f"Response after COMPLETE from EXPLAINING: {complete_response.get('state', 'unknown')}"
                )
                time.sleep(3)

                # Re-check state
                state_data = self.api_client.get_state()
                current_state = state_data.get("state", "UNKNOWN")
                print(f"State after COMPLETE from EXPLAINING: {current_state}")

            # 2. Handle CHAT state - need to send return to exit CHAT state
            if current_state == "CHAT":
                print("In CHAT state, sending 'return' to exit CHAT state...")
                return_response = self.api_client.submit_answer("return")
                print(
                    f"Response after 'return' from CHAT: {return_response.get('state', 'unknown')}"
                )
                time.sleep(3)

                # Re-check state
                state_data = self.api_client.get_state()
                current_state = state_data.get("state", "UNKNOWN")
                print(f"State after 'return' from CHAT: {current_state}")

            # Keep trying until successfully enter EVALUATING state
            max_attempts = 5
            for attempt in range(max_attempts):
                # Send END_EXAM to enter evaluation state
                print(
                    f"Sending END_EXAM to enter evaluation state (attempt {attempt+1}/{max_attempts})..."
                )
                end_response = self.api_client.submit_answer("END_EXAM")
                print(f"Response state after END_EXAM: {end_response.get('state', 'unknown')}")

                # Wait for state transition to complete
                time.sleep(3)

                # Check current state
                state_data = self.api_client.get_state()
                current_state = state_data.get("state", "UNKNOWN")
                print(f"Current state after END_EXAM: {current_state}")

                # If already in EVALUATING state, exit loop
                if current_state == "EVALUATING":
                    print("Successfully entered EVALUATING state")
                    break

                # If still in EXPLAINING state, need to send COMPLETE first
                if current_state == "EXPLAINING":
                    print("Still in EXPLAINING state, sending COMPLETE first...")
                    self.api_client.submit_answer("COMPLETE")
                    time.sleep(3)
                    continue

                # If still not in EVALUATING state, wait a bit and try again
                print(f"Not in EVALUATING state yet, waiting... (current state: {current_state})")
                time.sleep(3)

            # Send COMPLETE to complete the exam
            print("Sending COMPLETE to complete the exam...")
            complete_response = self.api_client.submit_answer("COMPLETE")
            print(f"Response state after COMPLETE: {complete_response.get('state', 'unknown')}")

            # Wait for evaluation to complete - increase wait time
            time.sleep(5)

            # Try to get evaluation result
            print("Getting evaluation results...")
            for retry in range(10):  # Increase retry count
                try:
                    evaluation = self.api_client.get_evaluation()
                    if evaluation.get("data") and "total_score" in evaluation.get("data", {}):
                        test_record["evaluation"] = evaluation
                        # Print evaluation summary
                        total_score = evaluation["data"].get("total_score", 0)
                        final_level = evaluation["data"].get("final_level", "Unknown")
                        print(f"Total score: {total_score}, Final level: {final_level}")

                        # Print evaluation data directly for debugging
                        print(f"Evaluation data retrieved and saved successfully")

                        # Check if answered questions number reaches minimum requirement (5)
                        if len(test_record["questions"]) >= 5:
                            # Save this evaluation data to test record
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
                        # If retry count exceeds half, try sending COMPLETE again to trigger evaluation
                        if retry >= 3 and retry % 2 == 1:
                            print("Sending COMPLETE again to trigger evaluation...")
                            self.api_client.submit_answer("COMPLETE")
                except Exception as e:
                    print(f"Error during evaluation retrieval: {str(e)}")

                time.sleep(3 + retry)  # Gradually increase wait time

            if not test_record.get("evaluation"):
                print("Warning: No valid evaluation data received.")

                # Try to get progress evaluation
                try:
                    print("Trying to get progress evaluation instead...")
                    progress = self.api_client.get_state()
                    if progress.get("data") and "context" in progress.get("data", {}):
                        context = progress["data"]["context"]
                        print(f"Progress context: {context}")
                        test_record["progress_context"] = context

                        # Still add to results even without complete evaluation
                        # Only add when answered questions number reaches minimum requirement (5)
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
        """Save intermediate test results"""
        result_file = os.path.join(
            self.output_dir,
            f"{student_type}_test_{test_num}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )

        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(test_record, f, ensure_ascii=False, indent=2)

        print(f"Test results saved to: {result_file}")

    def _save_final_results(self):
        """Save final experiment results"""
        result_file = os.path.join(
            self.output_dir, f"experiment_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print(f"Final experiment results saved to: {result_file}")

    def analyze_results(self):
        """Analyze experiment results"""
        print("\n===== Experiment Results Analysis =====")

        # Summary information
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

        # Extract evaluation scores
        scores = {}
        for student_type, tests in self.results.items():
            scores[student_type] = []
            print(f"Processing {len(tests)} tests for student type: {student_type}")

            for test in tests:
                # Only include in statistics when answered questions number reaches minimum requirement
                if len(test.get("questions", [])) < 5:
                    print(f"  - Skipping test with only {len(test.get('questions', []))} questions")
                    continue

                if test.get("evaluation") and "data" in test["evaluation"]:
                    total_score = test["evaluation"]["data"].get("total_score", 0)
                    scores[student_type].append(total_score)
                    print(f"  - Found score: {total_score}")
                else:
                    print(f"  - Test without valid evaluation data")

            # Calculate average and standard deviation
            if scores[student_type]:
                avg = sum(scores[student_type]) / len(scores[student_type])
                std = statistics.stdev(scores[student_type]) if len(scores[student_type]) > 1 else 0
                print(f"{student_type} student average score: {avg:.2f} ± {std:.2f}")
            else:
                print(f"{student_type} student: No valid evaluation data")

        # Generate analysis charts
        self._generate_visualizations(scores)

    def _generate_visualizations(self, scores):
        """Generate visual charts"""
        # Fix: Even if not all student types have data, visualizations are generated
        valid_data = False
        for student_scores in scores.values():
            if student_scores:
                valid_data = True
                break

        if not valid_data:
            print("Insufficient data to generate visualizations")
            return

        # Extract final_score and final_level data
        final_scores = {}
        final_levels = {}
        level_mapping = {"Excellent": 1.0, "Good": 0.5, "Fair": 0, "Poor": -0.5}

        for student_type, tests in self.results.items():
            final_scores[student_type] = []
            final_levels[student_type] = []

            for test in tests:
                # Only include in statistics when answered questions number reaches minimum requirement
                if len(test.get("questions", [])) < 5:
                    continue

                if test.get("evaluation") and "data" in test["evaluation"]:
                    eval_data = test["evaluation"]["data"]

                    # Extract final_score
                    if "final_score" in eval_data:
                        final_scores[student_type].append(eval_data["final_score"])
                    # Try other possible field names
                    elif "finalScore" in eval_data:
                        final_scores[student_type].append(eval_data["finalScore"])
                    elif "final_result" in eval_data:
                        final_scores[student_type].append(eval_data["final_result"])
                    elif "score" in eval_data:
                        final_scores[student_type].append(eval_data["score"])
                    # If still not found, try using total_score as backup
                    elif "total_score" in eval_data:
                        final_scores[student_type].append(eval_data["total_score"])

                    # Extract final_level and convert to numeric value
                    level_found = False
                    # Try different possible field names
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

                            # Handle different formats (case, space, etc.)
                            if isinstance(level, str):
                                level_key = level.strip().title()
                                if level_key in level_mapping:
                                    final_levels[student_type].append(level_mapping[level_key])
                                else:
                                    # Try partial match
                                    for k, v in level_mapping.items():
                                        if k.lower() in level.lower():
                                            final_levels[student_type].append(v)
                                            break
                                    else:
                                        print(f"Could not match level: {level}")
                            elif isinstance(level, (int, float)):
                                # If numeric, check if it's within our mapping range
                                if level in level_mapping.values():
                                    final_levels[student_type].append(level)
                                else:
                                    # Try mapping to closest value
                                    closest = min(
                                        level_mapping.values(), key=lambda x: abs(x - level)
                                    )
                                    final_levels[student_type].append(closest)
                                    print(
                                        f"Mapped numeric level {level} to closest value: {closest}"
                                    )

                    # If no level found, try to infer from other information
                    if not level_found and "total_score" in eval_data:
                        score = eval_data["total_score"]
                        # Based on score range infer level
                        if score >= 85:
                            final_levels[student_type].append(level_mapping["Excellent"])
                        elif score >= 70:
                            final_levels[student_type].append(level_mapping["Good"])
                        elif score >= 55:
                            final_levels[student_type].append(level_mapping["Fair"])
                        else:
                            final_levels[student_type].append(level_mapping["Poor"])

        # Create a larger figure, containing 6 subplots
        plt.figure(figsize=(20, 15))

        # Only process student types with data
        student_types = [st for st in scores.keys() if scores[st]]
        if not student_types:
            return

        # Directly use English type names, no need to map

        # 1. Score comparison chart (Total Score)
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

        # Display specific scores on bar chart
        for bar, score in zip(bars, avg_scores):
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 5,
                f"{score:.1f}",
                ha="center",
                va="bottom",
            )

        # 2. Score distribution chart (Total Score)
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

        # 3. Final Score comparison chart
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

            # Display specific scores on bar chart
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

        # 4. Final Level comparison chart
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

            # Add horizontal reference lines and labels
            plt.axhline(y=1.0, color="r", linestyle="-", alpha=0.3)
            plt.axhline(y=0.5, color="r", linestyle="-", alpha=0.3)
            plt.axhline(y=0.0, color="r", linestyle="-", alpha=0.3)
            plt.axhline(y=-0.5, color="r", linestyle="-", alpha=0.3)

            plt.text(len(level_types) - 1, 1.0, "Excellent", ha="right", va="bottom", color="r")
            plt.text(len(level_types) - 1, 0.5, "Good", ha="right", va="bottom", color="r")
            plt.text(len(level_types) - 1, 0.0, "Fair", ha="right", va="bottom", color="r")
            plt.text(len(level_types) - 1, -0.5, "Poor", ha="right", va="bottom", color="r")

            # Display specific scores on bar chart
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

        # 5. Score scatter plot (original 3rd chart)
        plt.subplot(3, 2, 5)
        for i, st in enumerate(student_types):
            x = [i] * len(scores[st])
            plt.scatter(x, scores[st], alpha=0.7)
        plt.xticks(range(len(student_types)), student_types)
        plt.title("Scatter Plot of Scores for Each Student Type")
        plt.ylabel("Score")
        plt.ylim(0, 100)

        # 6. Student type discrimination analysis (original 4th chart)
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

        # Save chart
        plt.tight_layout()
        plt.savefig(
            os.path.join(
                self.output_dir,
                f'experiment_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png',
            )
        )
        plt.close()

        print(f"Analysis charts saved to: {self.output_dir}")

        # Extra create a pie chart to display final_level distribution for each student type
        try:
            if any(final_levels.values()):  # Ensure at least some level data
                plt.figure(figsize=(15, 10))

                # Replace pie chart with point chart, visually display different student type evaluation level distribution
                student_type_list = []
                level_values_list = []
                level_labels_list = []

                # Collect all data points
                for student_type in self.results.keys():
                    if student_type not in final_levels or not final_levels[student_type]:
                        continue

                    for level_value in final_levels[student_type]:
                        student_type_list.append(student_type)
                        level_values_list.append(level_value)

                        # Add label to each point
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

                # Create data frame for point chart
                level_data = pd.DataFrame(
                    {
                        "Student Type": student_type_list,
                        "Level Value": level_values_list,
                        "Level": level_labels_list,
                    }
                )

                # Different level corresponds to different colors
                colors = {
                    "Excellent": "#66b3ff",
                    "Good": "#99ff99",
                    "Fair": "#ffcc99",
                    "Poor": "#ff9999",
                }

                # Draw point chart
                plt.figure(figsize=(12, 8))

                # Slightly jitter points to make overlapping points visible
                for level, color in colors.items():
                    mask = level_data["Level"] == level
                    if any(mask):
                        # Add small random jitter to x coordinates to make overlapping points visible
                        x_jittered = [
                            student_type + np.random.normal(0, 0.05)
                            for student_type in level_data.loc[mask, "Student Type"]
                        ]

                        plt.scatter(
                            x=x_jittered,
                            y=level_data.loc[mask, "Level Value"],
                            color=color,
                            label=level,
                            s=100,  # Point size
                            alpha=0.7,  # Transparency
                            edgecolors="black",  # Point edge color
                            linewidth=1,  # Edge line width
                        )

                # Add horizontal reference lines and labels
                plt.axhline(y=1.0, color="#66b3ff", linestyle="-", alpha=0.3)
                plt.axhline(y=0.5, color="#99ff99", linestyle="-", alpha=0.3)
                plt.axhline(y=0.0, color="#ffcc99", linestyle="-", alpha=0.3)
                plt.axhline(y=-0.5, color="#ff9999", linestyle="-", alpha=0.3)

                plt.text(-0.2, 1.0, "Excellent", ha="right", va="center", color="#66b3ff")
                plt.text(-0.2, 0.5, "Good", ha="right", va="center", color="#99ff99")
                plt.text(-0.2, 0.0, "Fair", ha="right", va="center", color="#ffcc99")
                plt.text(-0.2, -0.5, "Poor", ha="right", va="center", color="#ff9999")

                # Set y axis range and labels
                plt.ylim(-0.7, 1.2)
                plt.ylabel("Final Level")
                plt.xlabel("Student Type")
                plt.title("Distribution of Final Levels for Different Student Types")
                plt.legend()
                plt.grid(True, alpha=0.3)

                # Save point chart
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

        # Try to generate multi-dimensional ability radar chart, if enough data
        try:
            self._generate_radar_chart()
        except Exception as e:
            print(f"Error generating radar chart: {str(e)}")

    def _generate_radar_chart(self):
        """Generate multi-dimensional ability radar chart"""
        # Extract different dimension scores - remove Answer Completeness, only keep three dimensions
        dimensions = {"Accuracy": {}, "Clarity": {}, "Understanding": {}}

        valid_dimensions = False
        student_types_with_data = set()

        # First initialize empty lists for all student types
        for student_type in self.results.keys():
            for dimension in dimensions:
                dimensions[dimension][student_type] = []

        # Extract data from evaluation results
        for student_type, tests in self.results.items():
            has_data = False

            for test in tests:
                # Check if answered questions number reaches minimum requirement
                if len(test.get("questions", [])) < 5:
                    continue

                # Safety check, ensure evaluation data exists
                if not test.get("evaluation") or "data" not in test["evaluation"]:
                    continue

                try:
                    eval_data = test["evaluation"]["data"]

                    # Extract question evaluations
                    question_evals = eval_data.get("question_evaluations", {})
                    if not question_evals:
                        print(f"No question evaluations found for {student_type}")
                        continue

                    for q_id, q_eval in question_evals.items():
                        # Skip non-dictionary type evaluation data
                        if not isinstance(q_eval, dict):
                            continue

                        # Try to extract metrics from different possible locations
                        metrics = None
                        if "metrics" in q_eval and isinstance(q_eval["metrics"], dict):
                            metrics = q_eval["metrics"]
                        elif "details" in q_eval and isinstance(q_eval["details"], dict):
                            metrics = q_eval["details"]

                        if metrics:
                            # Handle different formats of numeric values (either number or "90/100" format)
                            for metric_name, metric_value in metrics.items():
                                try:
                                    dimension_key = None
                                    # Map metric name to dimension
                                    metric_name_lower = metric_name.lower()
                                    if (
                                        "accurate" in metric_name
                                        or "accuracy" in metric_name_lower
                                        or "准确" in metric_name
                                    ):
                                        dimension_key = "Accuracy"
                                    elif (
                                        "clear" in metric_name
                                        or "clarity" in metric_name_lower
                                        or "清晰" in metric_name
                                    ):
                                        dimension_key = "Clarity"
                                    elif (
                                        "understand" in metric_name
                                        or "understanding" in metric_name_lower
                                        or "理解" in metric_name
                                    ):
                                        dimension_key = "Understanding"

                                    if dimension_key and metric_value is not None:
                                        # Convert to float
                                        if isinstance(metric_value, (int, float)):
                                            value = float(metric_value)
                                        elif isinstance(metric_value, str) and "/" in metric_value:
                                            value = float(metric_value.split("/")[0])
                                        else:
                                            # Try to convert directly to float
                                            value = float(metric_value)

                                        dimensions[dimension_key][student_type].append(value)
                                        has_data = True
                                        valid_dimensions = True
                                        student_types_with_data.add(student_type)
                                except (ValueError, TypeError, IndexError) as e:
                                    # Print detailed error but continue processing
                                    print(f"Error parsing metric {metric_name}: {str(e)}")

                except Exception as e:
                    print(f"Error processing evaluation for {student_type}: {str(e)}")

        if not valid_dimensions:
            print("No valid dimension data for radar chart")
            return

        print(f"Student types with data: {student_types_with_data}")

        # Extract average values - Add more safety checks
        for dimension in dimensions:
            for student_type in self.results.keys():
                scores = dimensions[dimension].get(student_type, [])
                # Only calculate average when there's data
                if scores:
                    dimensions[dimension][student_type] = sum(scores) / len(scores)
                else:
                    # Ensure each student_type has value in each dimension
                    dimensions[dimension][student_type] = 0

        # Only include student types with data
        student_types = list(student_types_with_data)
        if not student_types:
            print("No student types with valid dimension data")
            return

        # Draw radar chart
        labels = list(dimensions.keys())
        angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
        angles += angles[:1]  # Close figure

        plt.figure(figsize=(10, 8))
        ax = plt.subplot(111, polar=True)

        # Use different colors to distinguish different student types
        colors = ["b", "r", "g", "c", "m", "y", "k"]

        # Draw line for each student type
        for i, student_type in enumerate(student_types):
            values = [dimensions[dim][student_type] for dim in labels]
            values += values[:1]  # Close data

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

        # Save chart
        radar_chart_filename = os.path.join(
            self.output_dir, f'radar_chart_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        )
        plt.savefig(radar_chart_filename)
        plt.close()

        print(f"Radar chart saved to: {radar_chart_filename}")

        # If not too much data, add simple text description
        if sum(len(dimensions[dim][st]) for dim in dimensions for st in student_types) < 10:
            print(
                "Limited data available for radar chart. Results may not be statistically significant."
            )


def main():
    """Main function"""
    # Check environment variable
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Please set it in the .env file or directly set the environment variable")
        return

    # Check if exam_questions.json file exists
    questions_file_found = False
    for path in [
        "/home/zhc/chatexaminer/data/exam_questions.json",
        "data/exam_questions.json",
        "../data/exam_questions.json",
        "exam_questions.json",
        os.path.join(os.getcwd(), "data", "exam_questions.json"),
    ]:
        if os.path.exists(path):
            print(f"Found exam_questions.json file: {path}")
            questions_file_found = True
            break

    if not questions_file_found:
        print("Warning: exam_questions.json file not found, context enhancement will be disabled")
        print("Please ensure to create this file in one of the following paths:")
        print("  - /home/zhc/chatexaminer/data/exam_questions.json")
        print("  - data/exam_questions.json")
        print("  - exam_questions.json")

    # Configure matplotlib support for Chinese characters
    try:
        # Try to set Chinese font
        import matplotlib as mpl

        # Check Chinese fonts on system
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
            # Use English labels as fallback
            print("Will use English labels as fallback.")

        plt.rcParams["axes.unicode_minus"] = False
    except Exception as e:
        print(f"Warning: Failed to configure matplotlib for Chinese: {str(e)}")
        print("Using English labels as fallback.")

    # Create experiment runner
    runner = ExperimentRunner()

    try:
        # Run experiment
        print("========== Starting AI Student Experiment ==========")
        print("Experiment settings:")
        print("  - Student type: Excellent(excellent), Average(average), Poor(poor)")
        print("  - Topic: Direct Methods for Optimal Control")
        print("  - Tests per student type: 3")
        print("  - Questions per test: 7")
        print("========================================")

        runner.run_experiment(
            student_types=["Excellent", "Average", "Poor"],
            topic="Direct Methods for Optimal Control",
            num_questions=7,  # Use 7 questions uniformly, ensure completeness
            tests_per_type=20,  # Adjust based on need
        )
        print("Experiment completed successfully!")
    except Exception as e:
        print(f"Experiment run error: {str(e)}")
        # Try to save any part of results
        try:
            if hasattr(runner, "results") and runner.results:
                print("Trying to save part of results...")
                runner._save_final_results()
                runner.analyze_results()
        except:
            print("Saving part of results failed.")


if __name__ == "__main__":
    main()
