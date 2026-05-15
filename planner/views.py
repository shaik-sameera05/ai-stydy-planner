from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from .models import StudyPlan


def home(request):
    return render(request, 'planner/home.html')


def register_view(request):

    message = ""

    if request.method == "POST":

        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']

        if User.objects.filter(username=username).exists():

            message = "Username already exists"

        else:

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )

            user.save()

            return redirect('/login/')

    return render(request, 'planner/register.html', {'message': message})


def login_view(request):

    message = ""

    if request.method == "POST":

        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)

            return redirect('/dashboard/')

        else:

            message = "Invalid Username or Password"

    return render(request, 'planner/login.html', {'message': message})


def dashboard(request):

    plan = ""
    message = ""

    if request.method == "POST":

        subject = request.POST['subject']
        exam_date = request.POST['exam_date']
        study_hours = request.POST['study_hours']

        if subject == "" or exam_date == "" or study_hours == "":

            message = "Please fill all fields"

        else:

            plan = f"""

Study Plan for {subject}

Morning:
Study for {study_hours} hours

Afternoon:
Practice important questions

Evening:
Revision and mock tests

Before Exam:
Complete full revision

"""

            StudyPlan.objects.create(
                subject=subject,
                exam_date=exam_date,
                study_hours=study_hours,
                generated_plan=plan
            )

    return render(
        request,
        'planner/dashboard.html',
        {
            'plan': plan,
            'message': message
        }
    )
def forgot_password(request):

    message = ""

    if request.method == "POST":

        username = request.POST['username']
        new_password = request.POST['new_password']

        try:

            user = User.objects.get(username=username)

            user.set_password(new_password)

            user.save()

            message = "Password Updated Successfully"

        except:

            message = "Username Not Found"

    return render(
        request,
        'planner/forgot.html',
        {'message': message}
    )