from planner.services import AIService, generate_student_plan, answer_student_question


class StudentPlannerAgent:
    def __init__(self, student):
        self.student = student

    def generate_plan(self, request_data):
        return generate_student_plan(self.student, request_data)

    def answer_question(self, question):
        return answer_student_question(self.student, question)

    def generate_quiz(self, subject_id, topic_id):
        from planner.services import create_quiz_for_student
        return create_quiz_for_student(self.student, subject_id, topic_id)

    def adapt_plan(self, reason='Progress-based plan adjustment'):
        from planner.services import adapt_future_plan
        return adapt_future_plan(self.student, reason)
