import sys
from pathlib import Path

# Add server directory to Python path
SERVER_DIR = Path(__file__).parent.parent.parent
sys.path.append(str(SERVER_DIR))

from app.services.exam_service import ExamService
from app.models.state_machine import ExamState
from app.scripts.state_detection_poc import analyze_response

def run_exam():
    exam_service = ExamService()
    state_machine = exam_service.state_machine
    
    print("Welcome to the Interactive Oral Examination System!")
    
    while True:
        current_state = state_machine.get_current_state()
        print(f"\nCurrent State: {current_state}")
        
        if current_state == ExamState.INIT:
            print("\nPlease enter the exam topic:")
            print("Available topics: Direct Methods for Optimal Control")
            student_response = input("Input: ").strip()
            
            if student_response.lower() == 'exit':
                break
                
            # Use analyze_response to determine state
            state_response = analyze_response(
                student_response, 
                current_state,
                state_machine.get_context()
            )
            
            if state_response.next_state == ExamState.TOPIC_SELECTED:
                state_machine.transition(
                    state_response.next_state,
                    metadata={
                        "topic": student_response,
                        "confidence": state_response.confidence,
                        "reason": state_response.reason
                    }
                )
            
        elif current_state == ExamState.TOPIC_SELECTED:
            print(f"\nSelected topic: {state_machine.context['topic']}")
            student_response = input("Are you ready to start? Please describe your preparation: ").strip()
            
            state_response = analyze_response(
                student_response,
                current_state,
                state_machine.get_context()
            )
            
            if state_response.next_state == ExamState.QUESTIONING:
                response = exam_service.start_exam(state_machine.context['topic'])
            elif state_response.next_state == ExamState.PREPARATION:
                state_machine.transition(state_response.next_state)
                
        elif current_state == ExamState.QUESTIONING:
            response = exam_service.get_next_interaction()
            if response["type"] == "question":
                print("\nQuestion:", response["content"])
                print(f"Difficulty Level: {response['difficulty']}/5")
                print("(If you want to end the exam, please explain why)")
                
                student_response = input("\nYour answer: ").strip()
                
                if student_response.lower() == 'exit':
                    break
                    
                state_response = analyze_response(
                    student_response,
                    current_state,
                    state_machine.get_context()
                )
                
                # Let OpenAI determine if we should end the exam
                if state_response.next_state == ExamState.EVALUATING:
                    print(f"\nState transition reason: {state_response.reason}")
                    state_machine.transition(
                        state_response.next_state,
                        metadata={
                            "confidence": state_response.confidence,
                            "reason": state_response.reason
                        }
                    )
                elif state_response.next_state == ExamState.EXPLAINING:
                    state_machine.transition(state_response.next_state)
                else:
                    response = exam_service.process_answer(student_response)
                    
        elif current_state == ExamState.EXPLAINING:
            print("\nExplanation needed...")
            student_response = input("Do you understand? Please describe: ").strip()
            
            state_response = analyze_response(
                student_response,
                current_state,
                state_machine.get_context()
            )
            
            if state_response.next_state == ExamState.QUESTIONING:
                state_machine.transition(state_response.next_state)
            
        elif current_state == ExamState.EVALUATING:
            print("\nGenerating evaluation report...")
            # TODO: Add evaluation report generation logic
            print("Evaluation Points:")
            print("1. Number of questions answered")
            print("2. Answer accuracy")
            print("3. Level of understanding")
            print("4. Number of hints requested")
            
            input("\nPress Enter to continue...")
            state_machine.transition(ExamState.COMPLETED)
            
        elif current_state == ExamState.COMPLETED:
            print("\nExam completed!")
            break
            
        elif current_state == ExamState.PREPARATION:
            print("\nPlease review the relevant content first.")
            student_response = input("Describe your preparation status: ").strip()
            
            state_response = analyze_response(
                student_response,
                current_state,
                state_machine.get_context()
            )
            
            state_machine.transition(state_response.next_state)

if __name__ == "__main__":
    run_exam() 