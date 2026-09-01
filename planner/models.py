from django.conf import settings
from django.db import models


class StudentProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    name = models.CharField(max_length=150, blank=True)
    college = models.CharField(max_length=150, blank=True)
    course = models.CharField(max_length=150, blank=True)
    year = models.PositiveIntegerField(default=1)
    daily_study_hours = models.PositiveIntegerField(default=2)
    learning_goal = models.TextField(blank=True)
    preferred_study_time = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name or self.user.username


class Subject(models.Model):
    DIFFICULTY_CHOICES = [
        (1, 'Beginner'),
        (2, 'Intermediate'),
        (3, 'Moderate'),
        (4, 'Advanced'),
        (5, 'Expert'),
    ]
    PRIORITY_CHOICES = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
    ]

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subjects')
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    difficulty = models.PositiveSmallIntegerField(choices=DIFFICULTY_CHOICES, default=3)
    priority = models.PositiveSmallIntegerField(choices=PRIORITY_CHOICES, default=2)
    target_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', 'name']
        unique_together = ('student', 'name')

    def __str__(self):
        return f'{self.student.username}: {self.name}'


class Topic(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='topics')
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    difficulty = models.PositiveSmallIntegerField(default=3)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ('subject', 'name')

    def __str__(self):
        return f'{self.subject.name}: {self.name}'


class StudyPlan(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ]

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='study_plans')
    title = models.CharField(max_length=150, default='AI Study Plan')
    start_date = models.DateField()
    end_date = models.DateField()
    total_hours = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.student.username}: {self.title}'


class StudyTask(models.Model):
    TASK_TYPE_CHOICES = [
        ('reading', 'Reading'),
        ('revision', 'Revision'),
        ('practice', 'Practice'),
        ('quiz', 'Quiz'),
        ('review', 'Review'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In progress'),
        ('completed', 'Completed'),
        ('skipped', 'Skipped'),
    ]

    plan = models.ForeignKey(StudyPlan, on_delete=models.CASCADE, related_name='tasks')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='tasks')
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    date = models.DateField()
    start_time = models.TimeField(default='09:00:00')
    duration = models.PositiveIntegerField(default=30)
    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES, default='practice')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'start_time']

    def __str__(self):
        return f'{self.subject.name} - {self.date}'


class Progress(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='progress_entries')
    task = models.OneToOneField(StudyTask, on_delete=models.CASCADE, related_name='progress')
    completion_percentage = models.PositiveIntegerField(default=0)
    score = models.FloatField(default=0.0)
    time_spent = models.PositiveIntegerField(default=0)
    confidence_level = models.PositiveSmallIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.student.username}: {self.task}'


class Quiz(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quizzes')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='quizzes')
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True, related_name='quizzes')
    title = models.CharField(max_length=150, default='Study Quiz')
    questions = models.JSONField(default=list)
    answers = models.JSONField(default=dict, blank=True)
    score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} - {self.score}%'


class AIInteraction(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_interactions')
    message = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.student.username} - {self.created_at}'
