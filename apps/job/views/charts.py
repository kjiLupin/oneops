
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def charts(request):
    return render(request, 'job/charts.html')
