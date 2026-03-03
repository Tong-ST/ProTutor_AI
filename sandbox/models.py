from django.db import models
from pydantic import BaseModel
from typing import List

# Create your models here.
class TestCase(BaseModel):
    name: str
    description: str
    input: str
    expected: str

class GradeRequest(BaseModel):
    code: str
    tests: List[TestCase]