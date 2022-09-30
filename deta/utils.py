import os
from typing import Optional

_project_key = None
_project_id = None


def _get_project_key_id(project_key: Optional[str] = None, project_id: Optional[str] = None):
    project_key = project_key or _project_key or os.getenv("DETA_PROJECT_KEY")

    if not project_key:
        raise ValueError("no project key defined")

    if not project_id:
        project_id = _project_id or project_key.split("_")[0]

    if project_id == project_key:
        raise ValueError("bad project key provided")

    return project_key, project_id


def _set_project_key_id(project_key: Optional[str] = None, project_id: Optional[str] = None):
    global _project_key, _project_id

    if project_key is not None:
        _project_key = project_key

    if project_id is not None:
        _project_id = project_id
