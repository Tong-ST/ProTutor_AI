from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor
import subprocess
import uuid
import os

app = FastAPI()

API_KEY = "YOUR_API_KEY"

# Limit concurrent executions
executor_pool = ThreadPoolExecutor(max_workers=2)


# ==========================
# Models
# ==========================

class CodeRequest(BaseModel):
    code: str
    input: str = ""


class TestCaseModel(BaseModel):
    input: str
    expected: str
    description: str | None = None  # <-- NEW


class GradeRequest(BaseModel):
    code: str
    tests: list[TestCaseModel]


# ==========================
# Utilities
# ==========================

def normalize_input(text: str) -> str:
    if text is None:
        return ""
    lines = text.replace("\r\n", "\n").split("\n")
    return "\n".join(line.lstrip() for line in lines)

def normalize(text: str):
    return text.strip().replace("\r\n", "\n")

# ==========================
# Core Executor
# ==========================

def execute_single_run(code: str, input_data: str):
    filename = f"/tmp/{uuid.uuid4().hex}.py"
    container_name = f"sandbox_{uuid.uuid4().hex}"

    with open(filename, "w") as f:
        f.write(code)

    try:
        process = subprocess.Popen(
            [
                "docker",
                "run",
                "--name", container_name,
                "--rm",
                "--memory=128m",
                "--cpus=0.5",
                "--pids-limit=64",
                "--network=none",
                "--read-only",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "-i",
                "-v",
                f"{filename}:/app/main.py:ro",
                "sandbox-python",
                "python",
                "/app/main.py",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            stdout, stderr = process.communicate(
                input=input_data,
                timeout=5
            )
        except subprocess.TimeoutExpired:
            subprocess.run(
                ["docker", "kill", container_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            process.kill()
            return {
                "status": "timeout",
                "stdout": "",
                "stderr": "",
            }

        return {
            "status": "success",
            "stdout": stdout[:5000],  # limit huge output
            "stderr": stderr[:5000],
        }

    except Exception as e:
        return {
            "status": "error",
            "stdout": "",
            "stderr": str(e),
        }

    finally:
        if os.path.exists(filename):
            os.remove(filename)



# ==========================
# Run Endpoint (Sandbox Mode)
# ==========================

@app.post("/run")
def run_code(request: CodeRequest, x_api_key: str = Header(None)):

    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")

    future = executor_pool.submit(
        execute_single_run,
        request.code,
        normalize_input(request.input)
    )

    return future.result()


# ==========================
# Grade Endpoint
# ==========================

@app.post("/grade")
def grade_code(request: GradeRequest, x_api_key: str = Header(None)):

    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        results = []

        for test in request.tests:
            clean_input = normalize_input(test.input)
            future = executor_pool.submit(
                execute_single_run,
                request.code,
                clean_input
            )
            result = future.result()

            if result["status"] == "timeout":
                results.append({
                    "description": test.description,
                    "passed": False,
                    "error": "Execution timed out"
                })
                continue

            if result["status"] != "success":
                results.append({
                    "description": test.description,
                    "passed": False,
                    "error": result["stderr"]
                })
                continue

            actual = normalize(result["stdout"])
            expected = normalize(test.expected)

            passed = actual == expected

            results.append({
                "description": test.description,
                "input": test.input,
                "expected": expected,
                "output": actual,
                "passed": passed
            })

        total = len(results)
        passed_count = sum(1 for r in results if r.get("passed"))

        return {
            "total": total,
            "passed": passed_count,
            "results": results
        }

    except Exception as e:
        print("VM CRASH:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
