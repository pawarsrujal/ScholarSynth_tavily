"""
In-memory storage for task states.
All data is lost on restart - no persistence.
"""
from typing import Dict, Optional
from models import TaskState
import threading


class MemoryStore:
    """Thread-safe in-memory storage for task states"""
    
    def __init__(self):
        self._store: Dict[str, TaskState] = {}
        self._lock = threading.RLock()
    
    def create(self, task_state: TaskState) -> TaskState:
        """Create a new task state"""
        with self._lock:
            self._store[task_state.task_id] = task_state
            return task_state
    
    def get(self, task_id: str) -> Optional[TaskState]:
        """Retrieve task state by ID"""
        with self._lock:
            return self._store.get(task_id)
    
    def update(self, task_id: str, task_state: TaskState) -> Optional[TaskState]:
        """Update existing task state"""
        with self._lock:
            if task_id in self._store:
                task_state.touch()
                self._store[task_id] = task_state
                return task_state
            return None
    
    def delete(self, task_id: str) -> bool:
        """Delete task state"""
        with self._lock:
            if task_id in self._store:
                del self._store[task_id]
                return True
            return False
    
    def list_all(self) -> Dict[str, TaskState]:
        """List all task states"""
        with self._lock:
            return dict(self._store)
    
    def clear(self):
        """Clear all task states"""
        with self._lock:
            self._store.clear()


# Global singleton instance
memory_store = MemoryStore()
