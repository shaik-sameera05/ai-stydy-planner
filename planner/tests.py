from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import AIInteraction, Progress, Quiz, StudentProfile, StudyPlan, StudyTask, Subject, Topic
from .services import (
    AIService,
    AIServiceError,
    adapt_future_plan,
    create_quiz_for_student,
    generate_plan_for_student,
    grade_quiz,
    update_task_progress,
)

User = get_user_model()


class PlannerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='student1', email='s1@example.com', password='secret123')
        self.client.login(username='student1', password='secret123')

    def test_registration_and_login(self):
        self.client.logout()
        response = self.client.post(
            reverse('register'),
            {'username': 'newstudent', 'email': 'new@example.com', 'password1': 'secret123', 'password2': 'secret123'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username='newstudent').exists())

        response = self.client.post(reverse('login'), {'username': 'newstudent', 'password': 'secret123'}, follow=True)
        self.assertRedirects(response, reverse('dashboard'))

    def test_profile_and_subject_topic_creation(self):
        profile_response = self.client.post(
            reverse('profile'),
            {
                'name': 'Student One',
                'college': 'Tech College',
                'course': 'Computer Science',
                'year': 2,
                'learning_goal': 'Become proficient in Python and algorithms.',
                'daily_study_hours': 4,
                'preferred_study_time': 'Evening',
            },
            follow=True,
        )
        self.assertEqual(profile_response.status_code, 200)
        self.assertTrue(StudentProfile.objects.filter(user=self.user, college='Tech College').exists())

        subject_response = self.client.post(
            reverse('subjects'),
            {
                'name': 'Python',
                'description': 'Core Python and algorithms.',
                'difficulty': 3,
                'priority': 3,
                'target_date': '2030-12-20',
            },
            follow=True,
        )
        self.assertEqual(subject_response.status_code, 200)
        self.assertTrue(Subject.objects.filter(student=self.user, name='Python').exists())

        subject = Subject.objects.get(student=self.user, name='Python')
        topic_response = self.client.post(
            reverse('topics'),
            {'subject': subject.id, 'name': 'Functions', 'description': 'Python function basics', 'difficulty': 2},
            follow=True,
        )
        self.assertEqual(topic_response.status_code, 200)
        self.assertTrue(Topic.objects.filter(subject=subject, name='Functions').exists())

    def test_study_plan_generation(self):
        subject = Subject.objects.create(
            student=self.user,
            name='Math',
            description='Algebra',
            difficulty=3,
            priority=3,
            target_date=date.today() + timedelta(days=12),
        )
        Topic.objects.create(subject=subject, name='Algebra', description='Linear equations', difficulty=2)
        payload = generate_plan_for_student(
            self.user,
            {
                'daily_study_hours': 2,
                'title': 'Plan',
                'start_date': str(date.today()),
                'end_date': str(date.today() + timedelta(days=7)),
            },
        )
        self.assertIn('tasks', payload)
        self.assertGreater(len(payload['tasks']), 0)

    def test_task_progress_update_and_calculation(self):
        subject = Subject.objects.create(
            student=self.user,
            name='Physics',
            description='Motion and force',
            difficulty=2,
            priority=2,
            target_date=date.today() + timedelta(days=9),
        )
        topic = Topic.objects.create(subject=subject, name='Forces', description='Force basics', difficulty=2)
        plan = StudyPlan.objects.create(
            student=self.user,
            title='Physics plan',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=5),
            total_hours=6,
            status='active',
        )
        task = StudyTask.objects.create(
            plan=plan,
            subject=subject,
            topic=topic,
            date=date.today(),
            start_time='09:00:00',
            duration=60,
            task_type='practice',
            priority='high',
            description='Review force equations',
            status='pending',
        )
        update_task_progress(self.user, task.id, 'completed', completion_percentage=80, score=85, time_spent=60, confidence_level=4)
        task = StudyTask.objects.get(id=task.id)
        self.assertEqual(task.status, 'completed')
        progress = Progress.objects.get(student=self.user, task=task)
        self.assertEqual(progress.completion_percentage, 80)
        self.assertEqual(progress.score, 85)

    def test_user_isolation_and_data_access(self):
        user2 = User.objects.create_user(username='student2', email='s2@example.com', password='pass456')
        Subject.objects.create(student=user2, name='Biology', description='Cells', difficulty=1, priority=2, target_date=date.today() + timedelta(days=10))
        self.client.logout()
        self.client.login(username='student2', password='pass456')
        self.assertEqual(Subject.objects.filter(student=self.user).count(), 0)
        self.assertEqual(Subject.objects.filter(student=user2).count(), 1)
        self.assertEqual(list(Subject.objects.filter(student=user2).values_list('name', flat=True)), ['Biology'])

    def test_quiz_workflow(self):
        subject = Subject.objects.create(
            student=self.user,
            name='Data Structures',
            description='Arrays and stacks',
            difficulty=3,
            priority=2,
            target_date=date.today() + timedelta(days=15),
        )
        topic = Topic.objects.create(subject=subject, name='Arrays', description='Array basics', difficulty=2)
        quiz = create_quiz_for_student(self.user, subject.id, topic.id)
        self.assertEqual(len(quiz.questions), 3)
        answers = {str(i): question['correct_index'] for i, question in enumerate(quiz.questions)}
        score = grade_quiz(quiz, answers)
        self.assertGreaterEqual(score, 0)
        self.assertEqual(quiz.score, score)
        self.assertTrue(Quiz.objects.filter(student=self.user, id=quiz.id).exists())

    def test_ai_error_handling(self):
        self.assertRaises(AIServiceError, AIService()._request, 'test', 'test')

    def test_adaptive_planning(self):
        subject = Subject.objects.create(
            student=self.user,
            name='Algorithms',
            description='Graphs and trees',
            difficulty=4,
            priority=3,
            target_date=date.today() + timedelta(days=20),
        )
        topic = Topic.objects.create(subject=subject, name='Graphs', description='Tree traversal', difficulty=3)
        plan = StudyPlan.objects.create(
            student=self.user,
            title='Graph plan',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=7),
            total_hours=8,
            status='active',
        )
        task = StudyTask.objects.create(
            plan=plan,
            subject=subject,
            topic=topic,
            date=date.today() + timedelta(days=1),
            start_time='10:00:00',
            duration=60,
            task_type='practice',
            priority='medium',
            description='Study graph traversal',
            status='pending',
        )
        Progress.objects.create(
            student=self.user,
            task=task,
            completion_percentage=20,
            score=30,
            time_spent=20,
            confidence_level=1,
        )
        result = adapt_future_plan(self.user)
        self.assertTrue(result['updated'])
        task.refresh_from_db()
        self.assertEqual(task.priority, 'high')
        self.assertTrue(AIInteraction.objects.filter(student=self.user).exists())
