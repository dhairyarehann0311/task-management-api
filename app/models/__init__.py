# Import models to ensure they are registered with SQLAlchemy metadata
from app.models.audit import AuditEvent 
from app.models.task import Tag, Task, TaskDependency, TaskTagLink, TaskUserLink  
from app.models.user import User
