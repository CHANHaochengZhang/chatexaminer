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
            if state == ExamState.INIT:
                print("\nPlease enter the exam topic:")
                print("Available topics: Direct Methods for Optimal Control")
                topic = input("Input: ")
                exam_service.state_machine.context["topic"] = topic
                exam_service.state_machine.transition(ExamState.TOPIC_SELECTED)

            elif state == ExamState.TOPIC_SELECTED:
                print(f"\nSelected topic: {exam_service.state_machine.context['topic']}")
                ready = input("Are you ready to start? Please describe your preparation: ")
                if ready.lower() not in ["no", "n"]:
                    response = await exam_service.start_exam(
                        exam_service.state_machine.context["topic"]
                    )

            elif state == ExamState.QUESTIONING:
                question = exam_service.state_machine.get_current_question()
                if question:
                    print(f"\nQuestion: {question['question']}")
                    print(f"Difficulty Level: {question['difficulty']}/5")
                    print("(If you want to end the exam, please explain why)")

                    answer = input("\nYour answer: ")
                    response = await exam_service.process_answer(answer)

            elif state == ExamState.EXPLAINING:
                print("\nExplanation needed...")
                understood = input("Do you understand? Please describe: ")
                if understood.lower() in ["yes", "y", "i understand"]:
                    exam_service.state_machine.transition(ExamState.QUESTIONING)

            elif state == ExamState.EVALUATING:
                print("\nGenerating final evaluation...")
                final_eval = exam_service._generate_final_evaluation()
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

            elif state == ExamState.COMPLETED:
                break

            elif state == ExamState.CHAT:
                print("\nSeems like we're having a casual conversation.")
                response = input("You can continue chatting or type 'return' to go back: ")

                if response.lower() == "return":
                    # 尝试返回到上一个有效状态
                    previous_state = exam_service.state_machine.context.get(
                        "previous_state", ExamState.INIT
                    )
                    exam_service.state_machine.transition(previous_state)
                else:
                    # 继续聊天，使用 state_detection 分析应该转到哪个状态
                    from app.scripts.state_detection_poc import analyze_response

                    result = await analyze_response(
                        response,
                        exam_service.state_machine.get_current_state(),
                        exam_service.state_machine.get_context(),
                    )
                    if result.next_state != ExamState.CHAT:
                        exam_service.state_machine.transition(result.next_state)

            else:
                # 处理未知状态，转到 CHAT 状态
                print("\nNot sure how to handle this interaction.")
                exam_service.state_machine.context["previous_state"] = state
                exam_service.state_machine.transition(ExamState.CHAT)

        except Exception as e:
            print(f"\nError: {str(e)}")
            # 发生错误时也转到 CHAT 状态
            exam_service.state_machine.context["previous_state"] = state
            exam_service.state_machine.transition(ExamState.CHAT)


if __name__ == "__main__":
    asyncio.run(main())
