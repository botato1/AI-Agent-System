# 업무 추출 / 업무 관리 관련 스키마
from typing import Optional, Literal
from pydantic import BaseModel, Field


# 업무 상태 값
TaskStatus = Literal["todo", "in_progress", "done", "delayed"]

# 업무 우선순위 값
TaskPriority = Literal["high", "medium", "low"]


# 할 일 하나의 구조
class TaskItemSchema(BaseModel):
    task_id: str                          # 업무 고유 ID
    task: str                             # 실제 할 일 내용
    assignee: Optional[str] = None        # 담당자, 없으면 None
    deadline: Optional[str] = None        # 마감일, 없으면 None
    status: TaskStatus = "todo"           # 업무 상태
    priority: TaskPriority = "medium"     # 우선순위
    room_id: Optional[str] = None          # 채팅방 ID
    document_id: Optional[str] = None      # 문서 ID
    created_at: Optional[str] = None       # 생성 시간


# 요약 + 할 일 추출 결과 구조
class TaskResultSchema(BaseModel):
    summary: Optional[str] = None
    tasks: list[TaskItemSchema] = Field(default_factory=list)


# 업무 직접 생성 요청 구조
class TaskCreateRequest(BaseModel):
    task: str = Field(..., min_length=1)          # 업무 내용은 필수
    assignee: Optional[str] = None                # 담당자
    deadline: Optional[str] = None                # 마감일
    status: TaskStatus = "todo"                   # 기본값 todo
    priority: TaskPriority = "medium"             # 기본값 medium
    room_id: Optional[str] = None                  # 채팅방 ID
    document_id: Optional[str] = None              # 문서 ID


# 업무 상태 변경 요청 구조
class TaskStatusUpdateRequest(BaseModel):
    status: TaskStatus


# 업무 우선순위 변경 요청 구조
class TaskPriorityUpdateRequest(BaseModel):
    priority: TaskPriority