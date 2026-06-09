# 업무 추출 결과 구조
from typing import Optional
from pydantic import BaseModel, Field


# 할 일 하나의 구조
class TaskItemSchema(BaseModel):
    task_id: str                          # 업무 고유 ID
    task: str                             # 실제 할 일 내용
    assignee: Optional[str] = None        # 담당자, 없으면 None
    deadline: Optional[str] = None        # 마감일, 없으면 None
    status: str = "todo"                  # 업무 상태: todo / doing / done


# 요약 + 할 일 추출 결과 구조
class TaskResultSchema(BaseModel):
    summary: Optional[str] = None                         # 회의록/문서 요약 결과
    tasks: list[TaskItemSchema] = Field(default_factory=list)  # 추출된 할 일 목록