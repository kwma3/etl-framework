from typing import Dict, Type, Any, List
from .base import ETLJob

class JobRegistry:
    """In-memory catalog of registered ETL jobs."""
    _CATALOG: Dict[str, Type[ETLJob]] = {}

    @classmethod
    def register(cls, name: str):
        """Decorator to register an ETLJob class."""
        def decorator(job_class: Type[ETLJob]):
            if name in cls._CATALOG:
                raise ValueError(f"Job '{name}' is already registered in catalog!")
            job_class.name = name
            cls._CATALOG[name] = job_class
            return job_class
        return decorator

    @classmethod
    def get(cls, name: str) -> ETLJob:
        """Retrieves and instantiates an ETL job instance by name."""
        if name not in cls._CATALOG:
            available = ", ".join(cls._CATALOG.keys()) or "None"
            raise KeyError(f"Job '{name}' not found. Available jobs: [{available}]")
        return cls._CATALOG[name]()

    @classmethod
    def list_jobs(cls) -> List[Dict[str, Any]]:
        """Returns metadata for all registered jobs."""
        results = []
        for name, job_cls in cls._CATALOG.items():
            job_inst = job_cls()
            results.append({
                "name": name,
                "description": job_cls.description,
                "tasks": [t.name for t in job_inst.tasks]
            })
        return results

register_job = JobRegistry.register
