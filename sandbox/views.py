import os
import requests
from django.shortcuts import render
from dotenv import load_dotenv

load_dotenv()

VM_URL = os.environ.get('VM_URL')
if not VM_URL:
    raise Exception("VM_URL not configured")

VM_URL_SUBMIT = os.environ.get('VM_URL_SUBMIT')
if not VM_URL_SUBMIT:
    raise Exception("VM_URL_SUBMIT not configured")

API_KEY = os.environ.get('X-API-KEY', default='None')
if not API_KEY:
    raise Exception("API_KEY not configured")

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

import json
from django.http import JsonResponse
from .testcases import ASSIGNMENTS

def submit_code_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    code = data.get("code")
    assignment_id = data.get("assignment_id")

    if not code:
        return JsonResponse({"error": "Missing code"}, status=400)

    if not assignment_id:
        return JsonResponse({"error": "Missing assignment_id"}, status=400)

    assignment = ASSIGNMENTS.get(int(assignment_id))

    if not assignment:
        return JsonResponse({"error": "Assignment not found"}, status=404)

    try:
        response = requests.post(
            VM_URL_SUBMIT,
            json={
                "code": code,
                "tests": assignment["tests"]
            },
            headers={
                "X-API-KEY": API_KEY
            },
            timeout=30
        )

        print("STATUS:", response.status_code)
        print("TEXT:", response.text)
        
        try:
            grading_result = response.json()
            for i, result in enumerate(grading_result.get("results", [])):
                if i < len(assignment["tests"]):
                    result["description"] = assignment["tests"][i].get("description", f"Test Case {i+1}")
        
        except ValueError:
            return JsonResponse({
                "error": "VM returned invalid JSON",
                "status_code": response.status_code,
                "raw_response": response.text
            }, status=500)

        return JsonResponse({
            "total": grading_result.get("total"),
            "passed": grading_result.get("passed"),
            "results": grading_result.get("results"),
            "assignment": {
                "id": assignment_id,
                "title": assignment["title"],
                "description": assignment.get("description", "")
            }
        })

    except requests.exceptions.Timeout:
        return JsonResponse({"error": "VM timeout"}, status=504)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)