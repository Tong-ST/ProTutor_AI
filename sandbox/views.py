import os
import requests
from django.shortcuts import render
from dotenv import load_dotenv

load_dotenv()

VM_URL = os.environ.get('VM_URL', default='None')
API_KEY = os.environ.get('X-API-KEY', default='None')


def run_code_view(request):
    output = None
    error = None
    code = ""

    if request.method == "POST":
        code = request.POST.get("code")

        try:
            response = requests.post(
                VM_URL,
                json={
                    "code": code,
                    "input": ""
                },
                headers={
                    "X-API-KEY": API_KEY
                },
                timeout=10
            )

            data = response.json()
            output = data.get("stdout")
            error = data.get("stderr") or data.get("error")

        except Exception as e:
            error = str(e)

    return render(request, "sandbox/run.html", {
        "output": output,
        "error": error,
        "code": code
    })