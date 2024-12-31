# Initialize RAG system
rag = ExaminerRAG(knowledge_base_path=Path("./knowledge_base"))

# Create exam context
exam_context = ExamContext(
    subject="Control Theory",
    difficulty_level=2,
    previous_questions=[],
    previous_answers=[],
    current_topic="PID Control",
)

# Generate question
response = rag.generate_question(exam_context)
print(f"Generated Question: {response.question}")

# Evaluate student answer
student_answer = (
    "PID controller achieves control through proportional, integral, and derivative terms..."
)
evaluation = rag.evaluate_answer(response.question, student_answer, exam_context)
print(f"Evaluation: {evaluation}")
