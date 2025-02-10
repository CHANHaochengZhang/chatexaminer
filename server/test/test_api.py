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
        print("\n=== Testing Evaluation Report Function ===")

        # 1. Start exam session
        print("\n1. Starting exam session...")
        start_response = requests.post(
            f"{BASE_URL}/start", json={"topic": "Direct Methods for Optimal Control"}
        )
        start_data = start_response.json()
        session_id = start_data["data"]["session_id"]
        print(f"Session ID: {session_id}")

        # 2. Submit multiple answers to generate evaluation data
        print("\n2. Submitting test answers...")
        test_answers = [
            "A nonlinear optimization problem is about optimizing something, like making a value as big or small as possible. There are some constraints, like how the system changes, limits on control variables, and some conditions to follow.",
            "I'm not sure about this one. Can I get a hint?",  # Request hint for second question
            "The resulting nonlinear programming problem can be solved using sequential quadratic programming.",
        ]

        for i, answer in enumerate(test_answers, 1):
            print(f"\nSubmitting answer {i}...")

            # If this is the second answer, request a hint first
            if i == 2:
                print("Requesting hint...")
                hint_response = requests.get(f"{BASE_URL}/{session_id}/hint")
                print(f"Hint response: {hint_response.json()}")
                time.sleep(1)  # Wait for hint to be processed

            answer_response = requests.post(
                f"{BASE_URL}/{session_id}/answer", json={"answer": answer}
            )
            response_data = answer_response.json()
            print(f"Answer {i} response status: {answer_response.status_code}")

            # Check current state
            state_response = requests.get(f"{BASE_URL}/{session_id}/state")
            state_data = state_response.json()
            print(f"Current exam state: {state_data['state']}")

            # Wait to ensure answer is processed
            time.sleep(1)

        # 3. Get progress evaluation
        print("\n3. Getting progress evaluation...")
        progress_response = requests.get(f"{BASE_URL}/{session_id}/progress")
        progress_data = progress_response.json()
        print("Progress evaluation:", json.dumps(progress_data, indent=2, ensure_ascii=False))

        # Transition to evaluation state
        print("\nTransitioning to evaluation state...")
        eval_transition_answer = "END_EXAM - I would like to end the exam now as I have answered all questions to the best of my ability. Please proceed with the final evaluation"
        eval_response = requests.post(
            f"{BASE_URL}/{session_id}/answer", json={"answer": eval_transition_answer}
        )
        print(
            "Transition response:", json.dumps(eval_response.json(), indent=2, ensure_ascii=False)
        )

        # Check if state has changed to evaluation
        state_response = requests.get(f"{BASE_URL}/{session_id}/state")
        current_state = state_response.json()["state"]
        print(f"Current state: {current_state}")

        if current_state != "EVALUATING":
            print("Waiting for state transition to evaluation...")
            time.sleep(2)
            # Try transition again
            eval_response = requests.post(
                f"{BASE_URL}/{session_id}/answer",
                json={"answer": "Yes, I'm ready for the evaluation."},
            )

        # Ensure exam completion
        print("\nSubmitting completion confirmation...")
        final_answer = (
            "END_EXAM Yes, I understand. I'm ready to complete the exam and receive my evaluation."
        )
        final_response = requests.post(
            f"{BASE_URL}/{session_id}/answer", json={"answer": final_answer}
        )
        print(
            "Completion response:", json.dumps(final_response.json(), indent=2, ensure_ascii=False)
        )

        # Wait for state update
        time.sleep(2)

        # 4. Get final evaluation report
        print("\n4. Getting final evaluation report...")
        eval_response = requests.get(f"{BASE_URL}/{session_id}/evaluation")
        eval_data = eval_response.json()

        if eval_data["data"]:
            print("\n=== Evaluation Report Details ===")
            print(f"Total Score: {eval_data['data'].get('total_score', 0):.2f}")
            print("\nTopic Coverage:")
            for topic, coverage in eval_data["data"].get("topic_coverage", {}).items():
                print(f"- {topic}: {coverage:.2f}%")

            print("\nQuestion Evaluations:")
            for qid, eval_info in eval_data["data"].get("question_evaluations", {}).items():
                print(f"\nQuestion {qid}:")
                print(f"Score: {eval_info.get('score', {})}")
                print(f"Feedback: {eval_info.get('feedback', '')}")
                print(f"Time taken: {eval_info.get('time_taken', 0):.2f} seconds")

            print("\nBehavioral Metrics:")
            behavior = eval_data["data"].get("session_metrics", {})
            print(f"Total time: {behavior.get('total_time', 0):.2f} seconds")
            print(f"Questions answered: {behavior.get('questions_answered', 0)}")
            print(f"Hints used: {behavior.get('hints_used', 0)}")
            print(f"Response consistency: {behavior.get('response_consistency', 0):.2f}")
        else:
            print("No evaluation report data received")
            print("Raw response:", json.dumps(eval_data, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"\nError: {str(e)}")


async def main():
    # Run original test
    # await test_exam_flow()

    # Run evaluation report test
    await test_exam_evaluation()


if __name__ == "__main__":
    asyncio.run(main())
