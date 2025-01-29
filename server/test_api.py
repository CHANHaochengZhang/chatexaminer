import asyncio
import json
import time

import requests
import websockets

BASE_URL = "http://localhost:8000/api/exam"


async def test_exam_flow():
    try:
        # 1. 启动考试
        print("\n1. 启动考试...")
        start_response = requests.post(
            f"{BASE_URL}/start", json={"topic": "Direct Methods for Optimal Control"}
        )
        start_data = start_response.json()
        print("响应:", json.dumps(start_data, indent=2, ensure_ascii=False))

        if start_response.status_code != 200:
            print("启动考试失败!")
            return

        session_id = start_data["data"]["session_id"]

        # 2. 获取状态
        print("\n2. 获取考试状态...")
        state_response = requests.get(f"{BASE_URL}/{session_id}/state")
        print("响应:", json.dumps(state_response.json(), indent=2, ensure_ascii=False))

        # 3. 提交答案
        print("\n3. 提交答案...")
        answer_response = requests.post(
            f"{BASE_URL}/{session_id}/answer", json={"answer": "这是一个测试答案"}
        )
        print("响应:", json.dumps(answer_response.json(), indent=2, ensure_ascii=False))

        # 4. WebSocket 测试
        print("\n4. WebSocket 测试...")
        async with websockets.connect(f"ws://localhost:8000/api/exam/{session_id}/ws") as ws:
            # 发送消息
            message = {"answer": "通过 WebSocket 发送的答案"}
            print("发送:", json.dumps(message, indent=2, ensure_ascii=False))
            await ws.send(json.dumps(message))

            # 接收响应
            response = await ws.recv()
            print("接收:", json.dumps(json.loads(response), indent=2, ensure_ascii=False))

            # 正常关闭连接
            await ws.close()

    except Exception as e:
        print(f"\n错误: {str(e)}")


async def test_exam_evaluation():
    try:
        print("\n=== 测试评估报告功能 ===")

        # 1. 启动考试会话
        print("\n1. 启动考试会话...")
        start_response = requests.post(
            f"{BASE_URL}/start", json={"topic": "Direct Methods for Optimal Control"}
        )
        start_data = start_response.json()
        session_id = start_data["data"]["session_id"]
        print(f"会话ID: {session_id}")

        # 2. 提交几个答案以生成评估数据
        print("\n2. 提交测试答案...")
        test_answers = [
            "The direct methods in optimal control transform the continuous problem into a discrete optimization problem.",
            "Collocation methods are commonly used, where the continuous functions are approximated at specific points.",
            "The resulting nonlinear programming problem can be solved using sequential quadratic programming.",
        ]

        for i, answer in enumerate(test_answers, 1):
            print(f"\n提交答案 {i}...")
            answer_response = requests.post(
                f"{BASE_URL}/{session_id}/answer", json={"answer": answer}
            )
            response_data = answer_response.json()
            print(f"答案 {i} 响应状态: {answer_response.status_code}")
            # print(f"答案 {i} 响应数据: {json.dumps(response_data, indent=2, ensure_ascii=False)}")

            # 检查当前状态
            state_response = requests.get(f"{BASE_URL}/{session_id}/state")
            state_data = state_response.json()
            print(f"当前考试状态: {state_data['state']}")

            # 等待一下确保答案被处理
            time.sleep(1)

        # 3. 获取进度评估
        print("\n3. 获取进度评估...")
        progress_response = requests.get(f"{BASE_URL}/{session_id}/progress")
        progress_data = progress_response.json()
        print("进度评估:", json.dumps(progress_data, indent=2, ensure_ascii=False))

        # 先转到评估状态
        print("\n转换到评估状态...")
        eval_transition_answer = "I believe I have answered all the questions thoroughly. Could we proceed to the evaluation?"
        eval_response = requests.post(
            f"{BASE_URL}/{session_id}/answer", json={"answer": eval_transition_answer}
        )
        print("转换响应:", json.dumps(eval_response.json(), indent=2, ensure_ascii=False))

        # 检查状态是否已转换到评估
        state_response = requests.get(f"{BASE_URL}/{session_id}/state")
        current_state = state_response.json()["state"]
        print(f"当前状态: {current_state}")

        if current_state != "EVALUATING":
            print("等待状态转换到评估...")
            time.sleep(2)
            # 再次尝试转换
            eval_response = requests.post(
                f"{BASE_URL}/{session_id}/answer",
                json={"answer": "Yes, I'm ready for the evaluation."},
            )

        # 确保考试完成
        print("\n提交结束确认...")
        final_answer = (
            "Yes, I understand. I'm ready to complete the exam and receive my evaluation."
        )
        final_response = requests.post(
            f"{BASE_URL}/{session_id}/answer", json={"answer": final_answer}
        )
        print("结束响应:", json.dumps(final_response.json(), indent=2, ensure_ascii=False))

        # 等待状态更新
        time.sleep(2)

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
                print(f"用时: {eval_info.get('time_taken', 0):.2f}秒")

            print("\n行为指标:")
            behavior = eval_data["data"].get("session_metrics", {})
            print(f"总用时: {behavior.get('total_time', 0):.2f}秒")
            print(f"答题数: {behavior.get('questions_answered', 0)}")
            print(f"使用提示数: {behavior.get('hints_used', 0)}")
            print(f"答案一致性: {behavior.get('response_consistency', 0):.2f}")
        else:
            print("未获取到评估报告数据")
            print("原始响应:", json.dumps(eval_data, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"\n错误: {str(e)}")


async def main():
    # 运行原有的测试
    # await test_exam_flow()

    # 运行评估报告测试
    await test_exam_evaluation()


if __name__ == "__main__":
    asyncio.run(main())
