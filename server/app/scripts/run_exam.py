import asyncio
import os
import sys
from pathlib import Path

# 获取当前脚本的绝对路径
current_file = Path(__file__).resolve()
# 获取 server 目录的路径
server_path = current_file.parent.parent.parent
# 将 server 目录添加到 Python 路径
sys.path.insert(0, str(server_path))

from app.models.state_machine import ExamState
from app.services.exam_service import ExamService
from dotenv import load_dotenv


async def main():
    print("Current working directory:", os.getcwd())
    env_path = Path(".env")
    print("Looking for .env at:", env_path.absolute())
    load_dotenv(env_path)

    exam_service = ExamService()

    print("Welcome to the Interactive Oral Examination System!\n")

    while True:
        state = exam_service.state_machine.get_current_state()
        print(f"\nCurrent State: {state}")

        try:
            # Display state-specific prompts
            if state == ExamState.INIT:
                print("\nPlease enter the exam topic:")
                print("Available topics: Direct Methods for Optimal Control")
                response = input("Input: ")
            elif state == ExamState.TOPIC_SELECTED:
                print(f"\nSelected topic: {exam_service.state_machine.context['topic']}")
                response = input("Are you ready to start? Please describe your preparation: ")
            elif state == ExamState.QUESTIONING:
                question = exam_service.state_machine.get_current_question()
                if question:
                    print(f"\nQuestion: {question['question']}")
                    print(f"Difficulty Level: {question['difficulty']}/5")
                    print("(If you want to end the exam, please explain why)")
                    response = input("\nYour answer: ")
                else:
                    response = "No more questions"
            elif state == ExamState.EXPLAINING:
                print("\nExplanation needed...")
                response = input("Do you understand? Please describe: ")
            elif state == ExamState.CHAT:
                print("\nSeems like we're having a casual conversation.")
                print("You can continue chatting or type 'return' to go back to the exam.")
                response = input("Chat: ")
            else:
                response = ""

            # Process response using function calling
            result = await exam_service.process_answer(response)

            # Handle response
            if isinstance(result, dict):
                if result.get("type") == "error":
                    print(f"\nError: {result['message']}")
                elif result.get("type") == "complete":
                    print("\nExam completed!")
                    if "evaluation" in result:
                        final_eval = result["evaluation"]
                        print("\nExam Results:")
                        print(f"Total Score: {final_eval['total_score']:.2f}")
                        print(f"Topic Coverage: {final_eval['topic_coverage']}")
                        print(f"Behavior Score: {final_eval['behavior_score']:.2f}")
                        print("\nDetailed Question Evaluations:")
                        for qid, eval_data in final_eval["question_evaluations"].items():
                            print(f"\nQuestion {qid}:")
                            print(f"Scores: {eval_data['score']}")
                            print(f"Feedback: {eval_data['feedback']}")
                    break
                elif result.get("type") == "state_change":
                    if result.get("content"):
                        print("\n" + result["content"])

        except Exception as e:
            print(f"\nError: {str(e)}")
            error_response = await exam_service.process_answer(f"Error occurred: {str(e)}")
            if isinstance(error_response, dict) and error_response.get("type") == "complete":
                break


if __name__ == "__main__":
    asyncio.run(main())
