from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from reporting.viewLogic import generate_bar_chart


@login_required
def report_generation(request):
    graph = generate_bar_chart()
    return render(request, "reporting/index.html", {"chart": graph})
