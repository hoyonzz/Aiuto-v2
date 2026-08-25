from enum import Enum



class TaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"

class Intent(str, Enum):
    TASK = "task"
    SCHEDULE = "schedule"
    MEMO = "memo"
    RESEARCH = "research"

class AiJobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"