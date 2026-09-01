import json
import os
import statistics
import urllib.error
import urllib.request
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import (
    AIInteraction,
    Progress,
    Quiz,
    StudentProfile,
    StudyPlan,
    StudyTask,
    Subject,
    Topic,
)

User = get_user_model()


class AIServiceError(Exception):
    pass


class ValidationError(Exception):
    pass


def get_or_create_profile(user):
    profile, _ = StudentProfile.objects.get_or_create(
        user=user,
        defaults={
            'name': user.get_full_name() or user.username,
            'daily_study_hours': 2,
            'preferred_study_time': 'Evening',
        },
    )
    return profile


def get_student_summary(user):
    profile = get_or_create_profile(user)
    subjects = Subject.objects.filter(student=user).prefetch_related('topics')
    tasks = StudyTask.objects.filter(plan__student=user).select_related('subject', 'topic', 'plan')
    completed = tasks.filter(status='completed').count()
    pending = tasks.filter(status='pending').count()
    total_hours = sum(task.duration for task in tasks)
    percentages = []
    for task in tasks:
        progress = getattr(task, 'progress', None)
        if progress:
            percentages.append(progress.completion_percentage)
    overall = round(sum(percentages) / len(percentages), 2) if percentages else 0
    return {
        'profile': profile,
        'subjects': list(subjects),
        'plans': list(StudyPlan.objects.filter(student=user).order_by('-created_at')),
        'tasks': list(tasks),
        'today_tasks': list(tasks.filter(date=timezone.localdate())),
        'completed_tasks': completed,
        'pending_tasks': pending,
        'total_hours': total_hours,
        'overall_progress': overall,
    }


def calculate_subject_progress(subject):
    tasks = StudyTask.objects.filter(subject=subject)
    if not tasks.exists():
        return 0
    percentages = []
    for task in tasks:
        progress = getattr(task, 'progress', None)
        if progress:
            percentages.append(progress.completion_percentage)
    return round(sum(percentages) / len(percentages), 2) if percentages else 0


def calculate_topic_progress(topic):
    tasks = StudyTask.objects.filter(topic=topic)
    if not tasks.exists():
        return 0
    percentages = []
    for task in tasks:
        progress = getattr(task, 'progress', None)
        if progress:
            percentages.append(progress.completion_percentage)
    return round(sum(percentages) / len(percentages), 2) if percentages else 0


def analyze_weak_topics(user):
    tasks = StudyTask.objects.filter(plan__student=user).select_related('subject', 'topic', 'plan')
    topic_data = {}
    for task in tasks:
        if not task.topic:
            continue
        entry = topic_data.setdefault(
            task.topic_id,
            {
                'subject': task.subject.name,
                'topic': task.topic.name,
                'scores': [],
                'completion': [],
                'confidence': [],
            },
        )
        progress = getattr(task, 'progress', None)
        if progress:
            if progress.completion_percentage is not None:
                entry['completion'].append(progress.completion_percentage)
            if progress.confidence_level is not None:
                entry['confidence'].append(progress.confidence_level)
            if progress.score is not None:
                entry['scores'].append(float(progress.score))

    weak = []
    for item in topic_data.values():
        score_avg = statistics.mean(item['scores']) if item['scores'] else 0
        completion_avg = statistics.mean(item['completion']) if item['completion'] else 0
        confidence_avg = statistics.mean(item['confidence']) if item['confidence'] else 0
        if completion_avg < 70 or score_avg < 70 or confidence_avg < 3:
            weak.append({
                'subject': item['subject'],
                'topic': item['topic'],
                'completion': round(completion_avg, 2),
                'score': round(score_avg, 2),
                'confidence': round(confidence_avg, 2),
                'reason': 'Low completion and weak performance.',
            })

    for quiz in Quiz.objects.filter(student=user):
        if quiz.topic and quiz.score < 70:
            if not any(item['topic'] == quiz.topic.name for item in weak):
                weak.append({
                    'subject': quiz.subject.name if quiz.subject else 'General',
                    'topic': quiz.topic.name,
                    'completion': 0,
                    'score': round(quiz.score, 2),
                    'confidence': 1,
                    'reason': 'Quiz performance is below target.',
                })
    return weak[:5]


def generate_recommendations(user):
    weak_topics = analyze_weak_topics(user)
    profile = get_or_create_profile(user)
    recommendations = []
    if weak_topics:
        for item in weak_topics[:3]:
            extra_minutes = max(30, 90 - int(item['score']))
            recommendations.append({
                'title': f'Focus on {item["topic"]}',
                'message': (
                    f'Your {item["topic"]} performance is below target. '
                    f'Allocate {extra_minutes} minutes to revision and practice tomorrow.'
                ),
            })
    else:
        recommendations.append({
            'title': 'Keep your momentum',
            'message': 'Your study consistency is strong. Maintain the current pace and add one recap block before the next assessment.',
        })
    if profile.daily_study_hours:
        recommendations.append({
            'title': 'Time distribution',
            'message': f'With {profile.daily_study_hours} study hours available, split your day into revision, practice, and recap blocks.',
        })
    return recommendations[:4]


def build_student_snapshot(user):
    profile = get_or_create_profile(user)
    subjects = Subject.objects.filter(student=user).prefetch_related('topics')
    payload = []
    for subject in subjects:
        payload.append({
            'id': subject.id,
            'name': subject.name,
            'priority': subject.priority,
            'difficulty': subject.difficulty,
            'target_date': subject.target_date.isoformat() if subject.target_date else None,
            'topics': [{'id': topic.id, 'name': topic.name, 'difficulty': topic.difficulty} for topic in subject.topics.all()],
        })
    return {
        'profile': {
            'name': profile.name,
            'college': profile.college,
            'course': profile.course,
            'year': profile.year,
            'learning_goal': profile.learning_goal,
            'daily_study_hours': profile.daily_study_hours,
            'preferred_study_time': profile.preferred_study_time,
        },
        'subjects': payload,
        'weak_topics': analyze_weak_topics(user),
        'recommendations': generate_recommendations(user),
        'tasks': [
            {
                'id': task.id,
                'subject': task.subject.name,
                'topic': task.topic.name if task.topic else None,
                'date': task.date.isoformat(),
                'status': task.status,
                'duration': task.duration,
                'priority': task.priority,
            }
            for task in StudyTask.objects.filter(plan__student=user).select_related('subject', 'topic', 'plan')
        ],
    }


class AIService:
    def __init__(self):
        self.api_key = os.getenv('AI_API_KEY') or os.getenv('OPENAI_API_KEY')
        self.base_url = os.getenv('AI_BASE_URL', 'https://api.openai.com/v1')
        self.model = os.getenv('AI_MODEL', 'gpt-4o-mini')

    def is_configured(self):
        return bool(self.api_key)

    def _request(self, system_prompt, user_prompt, temperature=0.3):
        if not self.api_key:
            raise AIServiceError('AI API is not configured. Add AI_API_KEY to your environment variables.')

        payload = {
            'model': self.model,
            'temperature': temperature,
            'response_format': {'type': 'json_object'},
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
        }
        request = urllib.request.Request(
            f'{self.base_url.rstrip("/")}/chat/completions',
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        try:
            with urllib.request.urlopen(request, timeout=40) as response:
                body = response.read().decode('utf-8')
        except urllib.error.HTTPError as exc:
            content = exc.read().decode('utf-8', errors='ignore')
            raise AIServiceError(f'AI request failed: {content[:200]}') from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise AIServiceError('AI service is unavailable right now. Please try again later.') from exc

        try:
            json_payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise AIServiceError('AI service returned malformed JSON.') from exc

        choices = json_payload.get('choices') or []
        if not choices:
            raise AIServiceError('AI service returned no choices.')
        content = (choices[0].get('message') or {}).get('content') or '{}'
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise AIServiceError('AI service returned invalid JSON. Please check the AI response format.') from exc


def validate_task_payload(task, student):
    if not isinstance(task, dict):
        raise ValidationError('Each study task must be an object.')

    required = ['date', 'subject', 'task', 'duration', 'priority', 'task_type']
    missing = [field for field in required if field not in task]
    if missing:
        raise ValidationError(f'Missing required fields: {missing}')

    try:
        task_date = date.fromisoformat(str(task['date']))
    except ValueError as exc:
        raise ValidationError('Each task requires a valid ISO date.') from exc

    duration = int(task.get('duration', 0))
    if duration <= 0:
        raise ValidationError('Each task duration must be greater than zero minutes.')

    subject_name = str(task['subject']).strip()
    subject = Subject.objects.filter(student=student, name__iexact=subject_name).first()
    if not subject:
        raise ValidationError(f'Subject not found for this student: {subject_name}')

    topic_name = task.get('topic')
    if topic_name:
        topic = Topic.objects.filter(subject=subject, name__iexact=str(topic_name).strip()).first()
        if not topic:
            raise ValidationError(f'Topic not found for subject {subject_name}: {topic_name}')

    task['subject_id'] = subject.id
    task['date_obj'] = task_date
    task['duration_int'] = duration
    task['priority'] = str(task.get('priority', 'medium')).lower()
    task['task_type'] = str(task.get('task_type', 'practice')).lower()
    task['description'] = str(task.get('description', task.get('task', 'Study task')))
    task['topic_name'] = str(topic_name).strip() if topic_name else None
    return task


def validate_plan_payload(payload, student):
    if not isinstance(payload, dict):
        raise ValidationError('AI plan response must be a JSON object.')
    tasks = payload.get('tasks')
    if not isinstance(tasks, list) or not tasks:
        raise ValidationError('AI plan must include at least one task.')
    payload['tasks'] = [validate_task_payload(task, student) for task in tasks]
    return payload


def save_validated_plan(student, payload, title, start_date, end_date, total_hours):
    validated = validate_plan_payload(payload, student)
    plan = StudyPlan.objects.create(
        student=student,
        title=title or 'AI study plan',
        start_date=start_date,
        end_date=end_date,
        total_hours=total_hours,
        status='active',
    )
    created_tasks = []
    for task in validated['tasks']:
        subject = Subject.objects.get(student=student, id=task['subject_id'])
        topic = None
        if task['topic_name']:
            topic = Topic.objects.filter(subject=subject, name__iexact=task['topic_name']).first()
        created_tasks.append(
            StudyTask.objects.create(
                plan=plan,
                subject=subject,
                topic=topic,
                date=task['date_obj'],
                start_time='09:00:00',
                duration=task['duration_int'],
                task_type=task['task_type'],
                priority=task['priority'],
                description=task['description'],
                status='pending',
            )
        )
    return plan, created_tasks


def ensure_student_profile(user):
    return get_or_create_profile(user)


def update_task_progress(user, task_id, status, completion_percentage=None, score=None, time_spent=None, confidence_level=None):
    task = StudyTask.objects.filter(plan__student=user, id=task_id).first()
    if not task:
        raise ValueError('Task not found.')

    task.status = status
    task.save(update_fields=['status', 'updated_at'])

    progress, _ = Progress.objects.get_or_create(student=user, task=task)
    if completion_percentage is not None:
        progress.completion_percentage = max(0, min(100, int(completion_percentage)))
    if score is not None:
        progress.score = max(0, min(100, float(score)))
    if time_spent is not None:
        progress.time_spent = max(0, int(time_spent))
    if confidence_level is not None:
        progress.confidence_level = max(1, min(5, int(confidence_level)))
    if completion_percentage is None and status == 'completed':
        progress.completion_percentage = 100
    progress.save()
    return task, progress


def build_quiz_payload(subject, topic, student):
    snapshot = build_student_snapshot(student)
    prompt = (
        f'Create 5 multiple choice questions on {subject.name} / {topic.name} for this student profile: {json.dumps(snapshot, default=str)}. '
        'Return JSON with {"questions": [{"question":"...","choices":["A","B","C","D"],"correct_index":1,"explanation":"..."}]}'
    )
    service = AIService()
    if not service.is_configured():
        return {
            'questions': [
                {
                    'question': f'What is a key concept in {topic.name}?',
                    'choices': ['Definition', 'Summary', 'Question', 'Outcome'],
                    'correct_index': 0,
                    'explanation': f'Review the core ideas of {topic.name} before the next practice block.',
                },
                {
                    'question': f'Which method best helps you review {topic.name}?',
                    'choices': ['Skip it', 'Practice active recall', 'Ignore confidence', 'Postpone all work'],
                    'correct_index': 1,
                    'explanation': 'Frequent active recall strengthens retention for difficult subjects.',
                },
                {
                    'question': f'How should you study {topic.name} most effectively?',
                    'choices': ['Randomly', 'By practicing and revising key concepts', 'By avoiding quizzes', 'By ignoring weak areas'],
                    'correct_index': 1,
                    'explanation': 'Practice and revision target weak points and improve recall.',
                },
            ]
        }
    response = service._request('You are an expert academic tutor. Return valid JSON only.', prompt)
    if not isinstance(response, dict) or 'questions' not in response:
        raise ValidationError('AI did not return a valid quiz structure.')
    questions = []
    for item in response['questions']:
        if not isinstance(item, dict):
            continue
        choices = item.get('choices')
        if not isinstance(choices, list) or len(choices) < 2:
            raise ValidationError('Each quiz question must include at least two choices.')
        correct_index = int(item.get('correct_index', -1))
        if correct_index < 0 or correct_index >= len(choices):
            raise ValidationError('Incorrect answer index in quiz data.')
        questions.append({
            'question': str(item.get('question', 'Question')),
            'choices': [str(choice) for choice in choices],
            'correct_index': correct_index,
            'explanation': str(item.get('explanation', '')),
        })
    response['questions'] = questions
    return response


def create_quiz_for_student(student, subject_id, topic_id):
    subject = Subject.objects.filter(student=student, id=subject_id).first()
    if not subject:
        raise ValueError('Invalid subject selected.')

    if topic_id:
        topic = Topic.objects.filter(subject__student=student, id=topic_id).first()
    else:
        topic = subject.topics.order_by('name').first()
    if not topic:
        raise ValueError('No topic found for that subject.')

    payload = build_quiz_payload(subject, topic, student)
    quiz = Quiz.objects.create(
        student=student,
        subject=subject,
        topic=topic,
        title=f'{subject.name} - {topic.name} quiz',
        questions=payload['questions'],
        score=0,
    )
    return quiz


def grade_quiz(quiz, submitted_answers):
    correct = 0
    total = len(quiz.questions)
    for index, question in enumerate(quiz.questions):
        answer = submitted_answers.get(str(index), submitted_answers.get(index))
        if answer is not None and int(answer) == int(question.get('correct_index', -1)):
            correct += 1
    score = round((correct / total) * 100, 2) if total else 0
    quiz.answers = submitted_answers
    quiz.score = score
    quiz.save(update_fields=['answers', 'score'])
    return score


def adapt_future_plan(student, reason='Recent progress indicates a change is needed.'):
    tasks = StudyTask.objects.filter(plan__student=student, status='pending', date__gte=timezone.localdate()).order_by('date')
    weak_topics = analyze_weak_topics(student)
    if not weak_topics:
        return {'updated': False, 'message': 'No weak topics were detected for adaptation.'}

    changed = 0
    for item in weak_topics[:2]:
        for task in tasks:
            if task.topic and task.topic.name == item['topic']:
                task.priority = 'high'
                task.description = f'{task.description} AI recommends extra revision for {item["topic"]}.'
                task.duration = min(max(task.duration, 60), 120)
                task.save(update_fields=['priority', 'duration', 'description', 'updated_at'])
                changed += 1

    AIInteraction.objects.create(
        student=student,
        message=reason,
        response=f'Updated {changed} pending tasks based on weak topic analysis.',
    )
    return {
        'updated': changed > 0,
        'message': f'AI updated your plan because {weak_topics[0]["topic"]} needs more attention.' if changed else 'No future tasks needed changes.',
        'count': changed,
    }


def answer_student_question(student, question):
    snapshot = build_student_snapshot(student)
    lower_question = question.lower()
    if 'plan' in lower_question and ('change' in lower_question or 'update' in lower_question or 'tomorrow' in lower_question):
        result = adapt_future_plan(student, f'User requested a plan adjustment: {question}')
        return {'answer': result.get('message', 'I adjusted your upcoming schedule.'), 'action': 'plan_updated', 'update': result}

    if not AIService().is_configured():
        weak = analyze_weak_topics(student)
        subject_names = ', '.join(subject['name'] for subject in snapshot['subjects']) or 'your subjects'
        if weak:
            answer = (
                f'Your current weak areas are {", ".join(item["topic"] for item in weak[:3])}. '
                f'For this week, focus on {weak[0]["topic"]} first and keep your daily study blocks within {snapshot["profile"]["daily_study_hours"]} hours.'
            )
        else:
            answer = f'You are currently studying {subject_names}. Keep your plan consistent and review the most difficult concept before the next quiz.'
        return {'answer': answer, 'action': 'no_ai', 'subjects': subject_names}

    system_prompt = 'You are a helpful study coach. Use only the student context provided and never invent data. Return valid JSON with {"answer":"...","action":"..."}.'
    prompt = f'Context: {json.dumps(snapshot, default=str)}. Question: {question}'
    response = AIService()._request(system_prompt, prompt)
    answer = response.get('answer', 'I could not generate a response.')
    AIInteraction.objects.create(student=student, message=question, response=answer)
    return response


def generate_student_plan(student, context):
    if not Subject.objects.filter(student=student).exists():
        raise ValidationError('Add at least one subject before generating a plan.')

    service = AIService()
    snapshot = build_student_snapshot(student)
    if not service.is_configured():
        subject_list = Subject.objects.filter(student=student).prefetch_related('topics')
        tasks = []
        for index, subject in enumerate(subject_list):
            topics = list(subject.topics.all()[:2]) or [None]
            for topic in topics:
                tasks.append({
                    'date': (date.today() + timedelta(days=index + 1)).isoformat(),
                    'subject': subject.name,
                    'topic': topic.name if topic else 'General review',
                    'task': f'Practice {subject.name} fundamentals',
                    'duration': max(30, min(90, subject.difficulty * 15)),
                    'priority': 'high' if subject.priority >= 3 else 'medium',
                    'task_type': 'practice',
                    'description': f'Review and practice {subject.name} with focused revision and active recall.',
                })
        return {'tasks': tasks[:5]}

    system_prompt = 'You are an expert academic planner. Use only the provided data and return valid JSON with a top-level "tasks" array.'
    prompt = (
        f'Context: {json.dumps(snapshot, default=str)}\n'
        f'Request: {json.dumps(context, default=str)}\n'
        'Return object {"tasks": [{"date":"YYYY-MM-DD","subject":"Subject Name","topic":"Topic Name","task":"Task title","duration":45,"priority":"high","task_type":"practice","description":"Short reason and objective"}]}'
    )
    payload = service._request(system_prompt, prompt)
    return validate_plan_payload(payload, student)


def generate_plan_for_student(student, context):
    return generate_student_plan(student, context)


def generate_recommendation_text(user):
    recs = generate_recommendations(user)
    return ' | '.join(item['message'] for item in recs) if recs else 'No recommendations available yet.'
