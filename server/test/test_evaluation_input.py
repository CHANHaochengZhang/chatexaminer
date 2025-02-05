import asyncio
import json
import time
from datetime import datetime
from typing import Dict

import requests

BASE_URL = "http://localhost:8000/api/exam"


async def interactive_exam_test():
    try:
        print("\n=== 交互式考试测试 ===")

        # 1. 开始考试
        print("\n正在开始考试...")
        start_response = requests.post(
            f"{BASE_URL}/start", json={"topic": "Direct Methods for Optimal Control"}
        )
        start_data = start_response.json()
        session_id = start_data["data"]["session_id"]
        print(f"考试会话ID: {session_id}")

        # 检查是否成功获取到第一个问题
        if not start_data["data"].get("current_question"):
            print("错误：无法获取第一个问题")
            return

        # 2. 进入答题循环
        question_count = 0
        while question_count < 5:  # 限制5个问题
            # 获取当前状态和问题
            state_response = requests.get(f"{BASE_URL}/{session_id}/state")
            state_data = state_response.json()
            current_question = state_data["data"].get("current_question")

            if not current_question:
                print("\n没有更多问题了")
                break

            print(f"\n问题 {question_count + 1}:")
            print(f"难度级别: {current_question.get('difficulty', '未知')}/5")
            print(f"问题内容: {current_question['question']}")

            # 提示用户输入
            while True:
                action = input("\n选择操作 (1: 回答问题, 2: 请求提示, 3: 查看进度): ")

                if action == "2":
                    # 请求提示
                    hint_response = requests.get(f"{BASE_URL}/{session_id}/hint")
                    hint_data = hint_response.json()
                    print("\n提示:", hint_data["data"]["hint"])
                    continue

                elif action == "3":
                    # 查看进度
                    progress_response = requests.get(f"{BASE_URL}/{session_id}/progress")
                    progress_data = progress_response.json()
                    print("\n=== 当前进度 ===")
                    print(f"已回答问题数: {progress_data['data']['stats']['questions_answered']}")
                    print(f"使用提示次数: {progress_data['data']['stats']['hints_requested']}")
                    print(f"当前难度: {progress_data['data']['stats']['current_difficulty']}")
                    continue

                elif action == "1":
                    break

                else:
                    print("无效的选择，请重试")

            # 获取用户答案
            print("\n请输入你的答案 (完成后按 Ctrl+D (Unix) 提交):")
            answer_lines = []
            try:
                while True:
                    try:
                        line = input()
                        answer_lines.append(line)
                    except EOFError:
                        print("\n答案已提交，正在处理...")
                        break
                answer = "\n".join(answer_lines)
            except KeyboardInterrupt:
                print("\n输入已取消")
                continue

            if not answer.strip():
                print("答案不能为空，请重试")
                continue

            # 提交答案
            print("\n正在提交答案...")
            answer_response = requests.post(
                f"{BASE_URL}/{session_id}/answer", json={"answer": answer}
            )
            response_data = answer_response.json()

            # 显示反馈
            if "data" in response_data and "result" in response_data["data"]:
                result = response_data["data"]["result"]
                if "feedback" in result:
                    print("\n反馈:", result["feedback"])

            question_count += 1
            time.sleep(1)  # 等待状态更新

        # 3. 获取最终评估
        print("\n正在生成最终评估...")
        # 发送完成信号
        final_response = requests.post(
            f"{BASE_URL}/{session_id}/answer",
            json={
                "answer": "I believe I have answered all the questions thoroughly. Could we proceed to the evaluation?"
            },
        )

        time.sleep(2)  # 等待评估生成

        eval_response = requests.get(f"{BASE_URL}/{session_id}/evaluation")
        eval_data = eval_response.json()

        if eval_data["data"]:
            print("\n=== 评估报告 ===")
            print(f"总分: {eval_data['data'].get('total_score', 0):.2f}")

            print("\n知识点覆盖:")
            for topic, coverage in eval_data["data"].get("topic_coverage", {}).items():
                print(f"- {topic}: {coverage:.2f}%")

            print("\n各题评估:")
            for qid, eval_info in eval_data["data"].get("question_evaluations", {}).items():
                print(f"\n问题 {qid}:")
                print(f"得分: {eval_info.get('score', {})}")
                print(f"反馈: {eval_info.get('feedback', '')}")
                print(f"用时: {eval_info.get('time_taken', 0):.2f} 秒")

            print("\n行为指标:")
            behavior = eval_data["data"].get("session_metrics", {})
            print(f"总用时: {behavior.get('total_time', 0):.2f} 秒")
            print(f"回答问题数: {behavior.get('questions_answered', 0)}")
            print(f"使用提示次数: {behavior.get('hints_used', 0)}")
            print(f"答题一致性: {behavior.get('response_consistency', 0):.2f}")
        else:
            print("未收到评估报告数据")
            print("原始响应:", json.dumps(eval_data, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"\n错误: {str(e)}")


if __name__ == "__main__":
    asyncio.run(interactive_exam_test())
