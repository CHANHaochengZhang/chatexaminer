import asyncio
import json
import time

import requests
import websockets

BASE_URL = "http://localhost:8000/api/exam"


async def test_exam_flow():
    try:
        # 1. Start exam
        print("\n1. Starting exam...")
        start_response = requests.post(
            f"{BASE_URL}/start", json={"topic": "Direct Methods for Optimal Control"}
        )
        start_data = start_response.json()
        print("Response:", json.dumps(start_data, indent=2, ensure_ascii=False))

        if start_response.status_code != 200:
            print("Failed to start exam!")
            return

        session_id = start_data["data"]["session_id"]

        # 2. Get state
        print("\n2. Getting exam state...")
        state_response = requests.get(f"{BASE_URL}/{session_id}/state")
        print("Response:", json.dumps(state_response.json(), indent=2, ensure_ascii=False))

        # 3. Submit answer
        print("\n3. Submitting answer...")
        answer_response = requests.post(
            f"{BASE_URL}/{session_id}/answer", json={"answer": "This is a test answer"}
        )
        print("Response:", json.dumps(answer_response.json(), indent=2, ensure_ascii=False))

        # 4. WebSocket test
        print("\n4. Testing WebSocket...")
        async with websockets.connect(f"ws://localhost:8000/api/exam/{session_id}/ws") as ws:
            # Send message
            message = {"answer": "Answer sent via WebSocket"}
            print("Sending:", json.dumps(message, indent=2, ensure_ascii=False))
            await ws.send(json.dumps(message))

            # Receive response
            response = await ws.recv()
            print("Received:", json.dumps(json.loads(response), indent=2, ensure_ascii=False))

            # Close connection normally
            await ws.close()

    except Exception as e:
        print(f"\nError: {str(e)}")


async def test_exam_evaluation():
    try:
        print("\n=== 测试评估报告功能 ===")

        # 准备6个标准答案
        test_answers = [
            # Q1: 直接配置法的主要优势
            "The main advantage of using direct collocation in optimal control is its ability to easily incorporate non-linear constraints and non-typical cost functions, making it particularly effective for trajectory optimization problems. This method directly applies to the dynamical model rather than a discrete approximation, which enhances its applicability in complex scenarios.",
            # Q2: 直接方法的主要关注点
            "The primary focus of direct methods in optimal control is to solve control problems by directly parameterizing the control trajectories and then optimizing them using numerical methods. This approach allows for the incorporation of constraints and objectives directly into the optimization process, leading to efficient solutions.",
            # Q3: 直接方法如何优化控制动作
            "Direct methods optimize control actions in reinforcement learning by formulating the control problem as an optimization task where the objective is to maximize the expected cumulative reward. These methods utilize parameterized policies and optimize them directly, often employing gradient ascent techniques to improve the performance of the learned policy.",
            # Q4: 探索与利用的平衡
            "Direct methods balance exploration and exploitation by iteratively refining control strategies through optimization techniques. They utilize simulations to evaluate different policies while optimizing the cost function, thus ensuring that both new strategies are explored and effective strategies are exploited.",
            # Q5: 直接方法相对于间接方法的优势
            "Direct methods in optimal control are advantageous because they allow for solving the optimization problem in a straightforward manner by directly manipulating the control variables. This can lead to faster convergence and more accurate solutions, as highlighted in the lecture materials.",
            # Q6: 直接方法的局限性
            "Direct methods in optimal control are advantageous because they allow for solving the optimization problem in a straightforward manner by directly manipulating the control variables. This can lead to faster convergence and more accurate solutions, as highlighted in the lecture materials.",
            # Q7: 直接方法相对于间接方法的优势
            "Direct methods in optimal control are advantageous because they allow for solving the optimization problem in a straightforward manner by directly manipulating the control variables. This can lead to faster convergence and more accurate solutions, as highlighted in the lecture materials.",
        ]

        # 1. 开始考试会话
        print("\n1. 开始考试会话...")
        start_response = requests.post(
            f"{BASE_URL}/start", json={"topic": "Direct Methods for Optimal Control"}
        )
        start_data = start_response.json()
        session_id = start_data["data"]["session_id"]
        print(f"会话ID: {session_id}")

        # 2. 提交答案
        print("\n2. 提交测试答案...")
        for i, answer in enumerate(test_answers, 1):
            print(f"\n提交答案 {i}/5...")

            # 等待30秒模拟学生思考和输入时间
            print(f"等待30秒模拟思考时间...")
            time.sleep(1)

            answer_response = requests.post(
                f"{BASE_URL}/{session_id}/answer", json={"answer": answer}
            )
            response_data = answer_response.json()
            print(f"答案 {i} 响应状态: {answer_response.status_code}")

            # 检查当前状态
            state_response = requests.get(f"{BASE_URL}/{session_id}/state")
            state_data = state_response.json()
            current_state = state_data["state"]
            print(f"当前考试状态: {current_state}")

            # 如果已经回答了所有问题，发送结束考试请求
            if i == len(test_answers):
                print("\n已回答所有问题，发送结束考试请求...")
                end_exam_response = requests.post(
                    f"{BASE_URL}/{session_id}/answer",
                    json={"answer": "END_EXAM"},
                )
                print(
                    "结束考试请求响应:",
                    json.dumps(end_exam_response.json(), indent=2, ensure_ascii=False),
                )

                # 再次检查状态
                state_response = requests.get(f"{BASE_URL}/{session_id}/state")
                state_data = state_response.json()
                current_state = state_data["state"]
                print(f"结束请求后的考试状态: {current_state}")

            # 如果状态已经变为EVALUATING或COMPLETED，说明考试已结束
            if current_state in ["EVALUATING", "COMPLETED"]:
                print("\n考试已结束，正在获取评估报告...")
                break

        # 4. 获取最终评估报告
        print("\n4. 获取最终评估报告...")
        eval_response = requests.get(f"{BASE_URL}/{session_id}/evaluation")
        eval_data = eval_response.json()

        if eval_data["data"]:
            print("\n=== 评估报告详情 ===")
            print(f"总分: {eval_data['data'].get('total_score', 0):.2f}")
            print("\n知识点覆盖:")
            for topic, coverage in eval_data["data"].get("topic_coverage", {}).items():
                print(f"- {topic}: {coverage:.2f}%")

            print("\n问题评估:")
            for qid, eval_info in eval_data["data"].get("question_evaluations", {}).items():
                print(f"\n问题 {qid}:")
                print(f"分数: {eval_info.get('score', {})}")
                print(f"反馈: {eval_info.get('feedback', '')}")
                print(f"用时: {eval_info.get('time_taken', 0):.2f} 秒")

            print("\n行为指标:")
            behavior = eval_data["data"].get("session_metrics", {})
            print(f"总用时: {behavior.get('total_time', 0):.2f} 秒")
            print(f"回答问题数: {behavior.get('questions_answered', 0)}")
            print(f"使用提示数: {behavior.get('hints_used', 0)}")
            print(f"答题一致性: {behavior.get('response_consistency', 0):.2f}")

            print("\n" + "=" * 50)
            print(f"最终总分: {eval_data['data'].get('total_score', 0):.2f}")
            print("=" * 50 + "\n")
        else:
            print("未收到评估报告数据")
            print("原始响应:", json.dumps(eval_data, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"\n错误: {str(e)}")


async def main():
    # Run original test
    # await test_exam_flow()

    # Run evaluation report test
    await test_exam_evaluation()


if __name__ == "__main__":
    asyncio.run(main())
