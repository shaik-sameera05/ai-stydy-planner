from django.db import models

class StudyPlan(models.Model):

    subject = models.CharField(max_length=100)

    exam_date = models.DateField()

    study_hours = models.IntegerField()

    generated_plan = models.TextField()

    def __str__(self):
        return self.subject