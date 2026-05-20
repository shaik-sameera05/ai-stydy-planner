from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from .models import StudyPlan


# HOME

def home(request):

    return render(
        request,
        'planner/home.html'
    )


# REGISTER

def register_view(request):

    message = ""

    if request.method == "POST":

        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if User.objects.filter(
            username=username
        ).exists():

            message = "Username already exists"

        else:

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )

            user.save()

            return redirect('/login/')

    return render(
        request,
        'planner/register.html',
        {'message': message}
    )


# LOGIN

def login_view(request):

    message = ""

    if request.method == "POST":

        username = request.POST.get('username')
        password = request.POST.get('password')

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

    return render(
        request,
        'planner/login.html',
        {'message': message}
    )


# DASHBOARD

def dashboard(request):

    return render(
        request,
        'planner/dashboard.html'
    )


# FORGOT PASSWORD

def forgot_password(request):

    message = ""

    if request.method == "POST":

        username = request.POST.get('username')
        new_password = request.POST.get('new_password')

        try:

            user = User.objects.get(
                username=username
            )

            user.set_password(
                new_password
            )

            user.save()

            message = "Password Updated Successfully"
            return redirect('/login/')

        except:

            message = "Username Not Found"

    return redirect('/login/')


# LOGOUT

def logout_view(request):

    logout(request)

    return redirect('/login/')