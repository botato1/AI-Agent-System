from fastapi import APIRouter

from backend.db.crud import (
    get_all_tasks,
    create_task,
    update_task_status,
    update_task_priority,
    delete_task,
)

from backend.schemas.task_schema import (
    TaskCreateRequest,
    TaskStatusUpdateRequest,
    TaskPriorityUpdateRequest,
)


router = APIRouter(
    prefix="/api",
    tags=["Tasks"]
)


# 전체 업무 목록 조회 API
@router.get("/tasks")
def get_task_list():
    try:
        rows = get_all_tasks()

        tasks = [
            {
                "task_id": row["id"],
                "task": row["task"],
                "assignee": row.get("assignee") or None,
                "deadline": row.get("deadline") or None,
                "status": row.get("status") or "todo",
                "priority": row.get("priority") or "medium",
                "room_id": row.get("conversation_id") or None,
                "document_id": row.get("document_id") or None,
                "created_at": row.get("created_at"),
            }
            for row in rows
        ]

        return {
            "tasks": tasks,
            "error": None
        }

    except Exception as e:
        print(f"[get_task_list 에러]: {str(e)}")

        return {
            "tasks": [],
            "error": "업무 목록 조회 중 오류가 발생했습니다."
        }


# 업무 직접 생성 API
@router.post("/tasks")
def create_task_api(request: TaskCreateRequest):
    try:
        task_data = request.model_dump()
        task_name = task_data["task"].strip()

        if not task_name:
            return {
                "task": None,
                "error": "업무 내용은 필수입니다."
            }

        created_task = create_task({
            **task_data,
            "task": task_name,
        })

        return {
            "task": created_task,
            "error": None
        }

    except Exception as e:
        print(f"[create_task_api 에러]: {str(e)}")

        return {
            "task": None,
            "error": "업무 생성 중 오류가 발생했습니다."
        }


# 업무 상태 변경 API
@router.patch("/tasks/{task_id}/status")
def update_task_status_api(task_id: str, request: TaskStatusUpdateRequest):
    try:
        updated = update_task_status(task_id, request.status)

        if not updated:
            return {
                "task": None,
                "error": "해당 업무를 찾을 수 없습니다."
            }

        return {
            "task": {
                "task_id": task_id,
                "status": request.status
            },
            "error": None
        }

    except Exception as e:
        print(f"[update_task_status_api 에러]: {str(e)}")

        return {
            "task": None,
            "error": "업무 상태 변경 중 오류가 발생했습니다."
        }


# 업무 우선순위 변경 API
@router.patch("/tasks/{task_id}/priority")
def update_task_priority_api(task_id: str, request: TaskPriorityUpdateRequest):
    try:
        updated = update_task_priority(task_id, request.priority)

        if not updated:
            return {
                "task": None,
                "error": "해당 업무를 찾을 수 없습니다."
            }

        return {
            "task": {
                "task_id": task_id,
                "priority": request.priority
            },
            "error": None
        }

    except Exception as e:
        print(f"[update_task_priority_api 에러]: {str(e)}")

        return {
            "task": None,
            "error": "업무 우선순위 변경 중 오류가 발생했습니다."
        }


# 업무 삭제 API
@router.delete("/tasks/{task_id}")
def delete_task_api(task_id: str):
    try:
        deleted = delete_task(task_id)

        if not deleted:
            return {
                "task": None,
                "error": "해당 업무를 찾을 수 없습니다."
            }

        return {
            "task": {
                "task_id": task_id,
                "deleted": True
            },
            "error": None
        }

    except Exception as e:
        print(f"[delete_task_api 에러]: {str(e)}")

        return {
            "task": None,
            "error": "업무 삭제 중 오류가 발생했습니다."
        }