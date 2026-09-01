from django import forms

from .models import StudentProfile, Subject, Topic


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = [
            'name',
            'college',
            'course',
            'year',
            'learning_goal',
            'daily_study_hours',
            'preferred_study_time',
        ]
        widgets = {
            'learning_goal': forms.Textarea(attrs={'rows': 4}),
        }


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'description', 'difficulty', 'priority', 'target_date']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'target_date': forms.DateInput(attrs={'type': 'date'}),
        }


class TopicForm(forms.ModelForm):
    class Meta:
        model = Topic
        fields = ['subject', 'name', 'description', 'difficulty']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
