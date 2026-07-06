from fastapi import FastAPI, status, Request, HTTPException
from enum import Enum
from typing import Optional, Any, Tuple
from fastapi.responses import JSONResponse
from datetime import datetime
from pydantic import BaseModel, Field

app = FastAPI()

tasks_db = [
    {
        "id": 1, 
        "title": "Thiet ke database Shop AI", 
        "description": "Xay dung bang va toi uu index", 
        "assignee": "QuyDev", 
        "priority": 1, 
        "status": "todo",
        "created_at": "2026-07-01T09:00:00Z"
    },
    {
        "id": 2, 
        "title": "Code bo API Authen", 
        "description": "Trien khai filter verify JWT token", 
        "assignee": "FixerQ", 
        "priority": 2, 
        "status": "done",
        "created_at": "2026-07-01T10:00:00Z"
    }
]

class TaskStatus(str, Enum):
    todo = "todo"
    done = "done"
    in_progress = "in_progress"

class TaskCreateSchema(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=1)
    assignee: str = Field(..., min_length=1)
    priority: int = Field(..., ge=1, le=5)

class TaskStatusUpdateSchema(BaseModel):
    status: TaskStatus

class BaseResponse(BaseModel):
    statusCode: int
    message: Optional[str]
    data: Optional[Any]
    error: Optional[Any]
    timestamp: str
    path: str

def create_response(status_code: int, message: Optional[str], data: Any, error: Any, request: Request):
    return BaseResponse(
        statusCode=status_code,
        message=message,
        data=data,
        error=error,
        timestamp=datetime.now().isoformat(),
        path=request.url.path
    ).model_dump()

@app.get("/tasks")
def get_all_tasks(request: Request, status_param: Optional[str] = None):
    if not status_param:
        response_data = tasks_db
    else:
        response_data = [task for task in tasks_db if task["status"] == status_param]

    return create_response(
        status_code=status.HTTP_200_OK,
        message="Lấy danh sách công việc thành công!",
        data=response_data,
        error=None,
        request=request
    )

@app.post("/tasks")
def create_task(task_in: TaskCreateSchema, request: Request):
    assignee_clean = task_in.assignee.strip()
    
    for task in tasks_db:
        if task["title"] == task_in.title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ERR-TASK-01: Task conflict: Title field duplicates an existing record."
            )
    
    max_id = max([task["id"] for task in tasks_db]) if tasks_db else 0
    
    new_task = {
        "id": max_id + 1,
        "title": task_in.title,
        "description": task_in.description,
        "assignee": assignee_clean,
        "priority": task_in.priority,
        "status": "todo",
        "created_at": datetime.now().isoformat()
    }
    
    tasks_db.append(new_task)
    
    return create_response(
        status_code=status.HTTP_201_CREATED,
        message="Khởi tạo công việc mới thành công!",
        data=new_task,
        error=None,
        request=request
    )

@app.put("/tasks/{task_id}")
def update_task_status(task_id: int, status_in: TaskStatusUpdateSchema, request: Request):
    target_task = None
    for task in tasks_db:
        if task["id"] == task_id:
            target_task = task
            break
            
    if target_task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ERR-TASK-03: Task not found."
        )
        
    if target_task["status"] == "done":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ERR-TASK-04: Cannot update status for a completed task."
        )
    
    target_task["status"] = status_in.status.value
    
    return create_response(
        status_code=status.HTTP_200_OK,
        message="Cập nhật tiến độ công việc thành công!",
        data=target_task,
        error=None,
        request=request
    )

def calculate_team_metrics() -> Tuple[int, int, float]:
    total_tasks = len(tasks_db)
    if total_tasks == 0:
        return (0, 0, 0.0)
        
    completed_tasks = sum(1 for task in tasks_db if task["status"] == "done")
    completion_rate_percentage = (completed_tasks / total_tasks) * 100
    
    return (total_tasks, completed_tasks, float(completion_rate_percentage))

@app.get("/tasks/analytics/dashboard")
def get_dashboard_analytics(request: Request):
    total, completed, rate = calculate_team_metrics()
    
    stats = {
        "total_tasks": total,
        "completed_tasks": completed,
        "completion_rate_percentage": rate
    }
    
    return create_response(
        status_code=status.HTTP_200_OK,
        message="Lấy số liệu thống kê hiệu suất nhóm thành công!",
        data=stats,
        error=None,
        request=request
    )

@app.exception_handler(422)
def validation_exception_handler(request: Request, exc: Any):
    response_body = create_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Lỗi: Dữ liệu đầu vào không hợp lệ hoặc sai định dạng quy định!",
        data=None,
        error="ERR-VAL-422: Validation error at Request Body fields constraint layout.",
        request=request
    )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=response_body)

@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    message = "Thực hiện yêu cầu thất bại"
    if "ERR-TASK-01" in str(exc.detail):
        message = "Lỗi: Tiêu đề công việc này đã tồn tại trong nhóm!"
    elif "ERR-TASK-03" in str(exc.detail):
        message = "Lỗi: Không tìm thấy ID công việc yêu cầu!"
    elif "ERR-TASK-04" in str(exc.detail):
        message = "Lỗi: Không thể cập nhật trạng thái lùi cho công việc đã hoàn thành!"

    response_body = create_response(
        status_code=exc.status_code,
        message=message,
        data=None,
        error=exc.detail,
        request=request
    )
    return JSONResponse(status_code=exc.status_code, content=response_body)

@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception):
    response_body = create_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="Hệ thống gặp sự cố không mong muốn!",
        data=None,
        error=f"Internal Server Error: {str(exc)}",
        request=request
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=response_body)