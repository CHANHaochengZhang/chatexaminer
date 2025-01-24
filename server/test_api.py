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


if __name__ == "__main__":
    asyncio.run(test_exam_flow())
