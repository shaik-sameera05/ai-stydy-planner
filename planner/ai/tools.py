import json

from django.db.models import Avg, Count

from planner.services import analyze_weak_topics, build_student_snapshot, generate_recommendations, get_student_summary


def get_student_profile(student):
    snapshot = build_student_snapshot(student)
    return snapshot['profile']


def get_student_subjects(student):
    return build_student_snapshot(student)['subjects']


def get_student_progress(student):
    summary = get_student_summary(student)
    return {
        'overall_progress': summary['overall_progress'],
        'completed_tasks': summary['completed_tasks'],
        'pending_tasks': summary['pending_tasks'],
        'total_hours': summary['total_hours'],
    }


def calculate_remaining_days(student):
    summary = get_student_summary(student)
    remaining = []
    for subject in summary['subjects']:
        if subject.target_date:
            remaining.append({'subject': subject.name, 'remaining_days': max(0, (subject.target_date - __import__('datetime').date.today()).days)})
    return remaining


def analyze_weak_topics_tool(student):
    return analyze_weak_topics(student)


def generate_recommendations_tool(student):
    return generate_recommendations(student)


def generate_ai_response(student, user_question):
    snapshot = build_student_snapshot(student)
    return {
        'answer': f'Based on your current profile and progress, focus on {snapshot["weak_topics"][0]["topic"] if snapshot["weak_topics"] else "your next exam topic"} next.',
        'action': 'recommendation',
        'question': user_question,
    }
