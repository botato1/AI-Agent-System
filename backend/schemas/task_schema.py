# 업무 추출 결과 구조
from typing import List, Optional
from pydantic import BaseModel


# 할 일 하나의 구조
class TaskItemSchema(BaseModel):
    task_id: str
    task: str
    assignee: Optional[str] = None
    deadline: Optional[str] = None
    status: str = "todo"


# 요약 + 할 일 추출 결과 구조
class TaskResultSchema(BaseModel):
    summary: Optional[str] = None
    tasks: List[TaskItemSchema]