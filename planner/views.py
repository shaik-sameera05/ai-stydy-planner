from datetime import date

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from .forms import StudentProfileForm, SubjectForm, TopicForm
from .models import AIInteraction, Quiz, StudyPlan, StudyTask, Subject, Topic
from .services import (
    AIServiceError,
    ValidationError,
    answer_student_question,
    ensure_student_profile,
    generate_plan_for_student,
    generate_recommendations,
    get_or_create_profile,
    get_student_summary,
    grade_quiz,
    save_validated_plan,
    update_task_progress,
)


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'planner/home.html')


def register_view(request):
    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        email = (request.POST.get('email') or '').strip()
        password1 = request.POST.get('password1') or ''
        password2 = request.POST.get('password2') or ''

        if not username or not email or not password1:
            messages.error(request, 'Please complete all required fields.')
        elif User.objects.filter(username__iexact=username).exists():
            messages.error(request, 'That username is already taken.')
        elif password1 != password2:
            messages.error(request, 'Passwords do not match.')
        else:
            user = User.objects.create_user(username=username, email=email, password=password1)
            user.save()
            messages.success(request, 'Registration successful. Please log in.')
            return redirect('login')

    return render(request, 'planner/register.html')


def login_view(request):
    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Welcome back!')
            return redirect('dashboard')
        messages.error(request, 'Invalid username or password.')
    return render(request, 'planner/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    profile = ensure_student_profile(request.user)
    summary = get_student_summary(request.user)
    from planner.services import analyze_weak_topics
    weak_topics = analyze_weak_topics(request.user)
    recommendations = generate_recommendations(request.user)
    recent_activity = AIInteraction.objects.filter(student=request.user).order_by('-created_at')[:8]
    tasks = StudyTask.objects.filter(plan__student=request.user).select_related('subject', 'topic', 'plan').order_by('date', 'start_time')[:10]
    today_tasks = [task for task in tasks if task.date == date.today()]
    context = {
        'profile': profile,
        'summary': summary,
        'weak_topics': weak_topics,
        'recommendations': recommendations,
        'recent_activity': recent_activity,
        'tasks': tasks,
        'today_tasks': today_tasks,
    }
    return render(request, 'planner/dashboard.html', context)


@login_required
def profile_view(request):
    profile = get_or_create_profile(request.user)
    if request.method == 'POST':
        form = StudentProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        form = StudentProfileForm(instance=profile)
    return render(request, 'planner/profile.html', {'form': form, 'profile': profile})


@login_required
def subjects_view(request):
    subjects = Subject.objects.filter(student=request.user).order_by('name')
    form = SubjectForm()
    if request.method == 'POST':
        if 'delete_id' in request.POST:
            subject = Subject.objects.filter(student=request.user, id=request.POST.get('delete_id')).first()
            if subject:
                subject.delete()
                messages.success(request, 'Subject removed.')
            return redirect('subjects')
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save(commit=False)
            subject.student = request.user
            subject.save()
            messages.success(request, 'Subject created successfully.')
            return redirect('subjects')
    return render(request, 'planner/subjects.html', {'subjects': subjects, 'form': form})


@login_required
def topics_view(request):
    topics = Topic.objects.filter(subject__student=request.user).select_related('subject').order_by('subject__name', 'name')
    form = TopicForm(initial={'subject': request.GET.get('subject_id')})
    if request.method == 'POST':
        if 'delete_id' in request.POST:
            topic = Topic.objects.filter(subject__student=request.user, id=request.POST.get('delete_id')).first()
            if topic:
                topic.delete()
                messages.success(request, 'Topic removed.')
            return redirect('topics')
        form = TopicForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            if subject.student != request.user:
                messages.error(request, 'You can only add topics to your own subjects.')
            else:
                form.save()
                messages.success(request, 'Topic added successfully.')
                return redirect('topics')
    return render(request, 'planner/topics.html', {'topics': topics, 'form': form})


@login_required
def study_plan_view(request):
    plans = StudyPlan.objects.filter(student=request.user).order_by('-created_at')
    tasks_by_plan = {}
    for plan in plans:
        tasks_by_plan[plan.id] = plan.tasks.select_related('subject', 'topic').all()
    return render(request, 'planner/study_plan.html', {'plans': plans, 'tasks_by_plan': tasks_by_plan})


@login_required
def generate_plan_view(request):
    if request.method != 'POST':
        return redirect('study_plan')

    title = (request.POST.get('title') or 'AI Study Plan').strip() or 'AI Study Plan'
    start_date = request.POST.get('start_date')
    end_date = request.POST.get('end_date')
    total_hours = request.POST.get('total_hours') or request.POST.get('daily_hours') or 0

    if not start_date or not end_date:
        messages.error(request, 'Please select a start and end date.')
        return redirect('study_plan')

    try:
        start_dt = date.fromisoformat(start_date)
        end_dt = date.fromisoformat(end_date)
        if end_dt < start_dt:
            raise ValueError
        total_hours_int = int(total_hours)
        if total_hours_int <= 0:
            raise ValueError
    except (TypeError, ValueError):
        messages.error(request, 'Please provide valid study dates and total hours.')
        return redirect('study_plan')

    context = {
        'title': title,
        'start_date': start_date,
        'end_date': end_date,
        'total_hours': total_hours_int,
        'daily_study_hours': ensure_student_profile(request.user).daily_study_hours,
    }

    try:
        payload = generate_plan_for_student(request.user, context)
        plan, tasks = save_validated_plan(request.user, payload, title, start_dt, end_dt, total_hours_int)
        AIInteraction.objects.create(
            student=request.user,
            message=f'Generated plan: {title}',
            response=f'Created {len(tasks)} tasks across {plan.start_date} to {plan.end_date}.',
        )
        messages.success(request, 'AI study plan generated and saved successfully.')
    except (AIServiceError, ValidationError, ValueError) as exc:
        messages.error(request, str(exc))
    return redirect('study_plan')


@login_required
def progress_view(request):
    tasks = StudyTask.objects.filter(plan__student=request.user).select_related('subject', 'topic', 'plan').order_by('date')
    summary = {
        'overall': 0,
        'completed': tasks.filter(status='completed').count(),
        'pending': tasks.filter(status='pending').count(),
        'in_progress': tasks.filter(status='in_progress').count(),
        'skipped': tasks.filter(status='skipped').count(),
    }
    percentages = []
    for task in tasks:
        progress = getattr(task, 'progress', None)
        if progress:
            percentages.append(progress.completion_percentage)
    if percentages:
        summary['overall'] = round(sum(percentages) / len(percentages), 2)
    return render(request, 'planner/progress.html', {'tasks': tasks, 'summary': summary})


@login_required
def task_update_view(request, task_id):
    if request.method != 'POST':
        return redirect('progress')
    status = request.POST.get('status') or 'pending'
    completion = request.POST.get('completion_percentage')
    score = request.POST.get('score')
    time_spent = request.POST.get('time_spent')
    confidence = request.POST.get('confidence_level')
    try:
        update_task_progress(
            request.user,
            task_id,
            status=status,
            completion_percentage=int(completion) if completion not in (None, '') else None,
            score=float(score) if score not in (None, '') else None,
            time_spent=int(time_spent) if time_spent not in (None, '') else None,
            confidence_level=int(confidence) if confidence not in (None, '') else None,
        )
        messages.success(request, 'Task progress updated.')
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect('progress')


@login_required
def quizzes_view(request):
    quizzes = Quiz.objects.filter(student=request.user).order_by('-created_at')
    subjects = Subject.objects.filter(student=request.user)
    return render(request, 'planner/quizzes.html', {'quizzes': quizzes, 'subjects': subjects})


@login_required
def generate_quiz_view(request):
    if request.method != 'POST':
        return redirect('quizzes')
    subject_id = request.POST.get('subject_id')
    topic_id = request.POST.get('topic_id')
    if not subject_id:
        messages.error(request, 'Select a subject before generating a quiz.')
        return redirect('quizzes')
    try:
        from planner.services import create_quiz_for_student
        quiz = create_quiz_for_student(request.user, int(subject_id), int(topic_id) if topic_id else 0)
        messages.success(request, 'AI quiz generated successfully.')
        return redirect('submit_quiz', quiz_id=quiz.id)
    except (ValueError, TypeError, ValidationError, AIServiceError) as exc:
        messages.error(request, str(exc))
        return redirect('quizzes')


@login_required
def submit_quiz_view(request, quiz_id):
    quiz = Quiz.objects.filter(student=request.user, id=quiz_id).first()
    if not quiz:
        messages.error(request, 'Quiz not found.')
        return redirect('quizzes')
    if request.method == 'POST':
        answers = {}
        for key, value in request.POST.items():
            if key.startswith('answer_'):
                index = key.split('_', 1)[1]
                answers[index] = int(value)
        score = grade_quiz(quiz, answers)
        messages.success(request, f'Quiz submitted. Score: {score}%.')
        AIInteraction.objects.create(
            student=request.user,
            message=f'Quiz result for {quiz.title}',
            response=f'You scored {score}% on the quiz.',
        )
        return redirect('quizzes')
    return render(request, 'planner/quiz_detail.html', {'quiz': quiz})


@login_required
def ai_assistant_view(request):
    result = None
    question = ''
    if request.method == 'POST':
        question = (request.POST.get('question') or '').strip()
        if not question:
            messages.error(request, 'Ask a study question to continue.')
            return render(request, 'planner/ai_assistant.html', {'result': result, 'question': question})
        result = answer_student_question(request.user, question)
        messages.success(request, 'AI assistant responded with a personalized answer.')
    return render(request, 'planner/ai_assistant.html', {'result': result, 'question': question})
