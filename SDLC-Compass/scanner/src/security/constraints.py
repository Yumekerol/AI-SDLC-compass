from __future__ import annotations

import zipfile
import os

from fastapi import UploadFile
from pathlib import Path

from ..models.constraint_output import ConstraintOutput, Result
from ..config import settings

# ZIP CONSTRAINT CHECKERS
def zip_file_format_constraint(file: UploadFile) -> ConstraintOutput:
    output = ConstraintOutput(result = Result.OK, message = "ok")
    
    supported_type: str = "application/zip"
    
    if file.content_type != supported_type:
        output.result = Result.WRONG_FORMAT
        output.message = f"Uploaded file '{file.filename}' has the wrong file format! Expected '{supported_type}', got '{file.content_type}'"
        return output
    
    return output

def zip_file_count_constraint(filepath: Path) -> ConstraintOutput:
    output = ConstraintOutput(result = Result.OK, message = "ok")
    
    filecount = 0
    with zipfile.ZipFile(filepath, "r") as file:
        for single in file.namelist():
            if not single.endswith('/' or '\\'):
                filecount += 1
    
    print(filecount)
    
    if filecount > settings.poc_max_files:
        output.result = Result.FILE_LIMIT
        output.message = f"Repository contains more files than allowed (>{settings.poc_max_files})."
    
    return output

def zip_file_depth_constraint(filepath: Path) -> ConstraintOutput:
    output = ConstraintOutput(result = Result.OK, message = "ok")

    max_depth = -1
    with zipfile.ZipFile(filepath, "r") as file:
        for elem in file.namelist():
            depth = elem.count("/" or "\\") # look for dashes indicating directories
            max_depth = max(max_depth, depth)
    
    if max_depth > settings.poc_max_depth:
        output.result = Result.DEPTH_LIMIT
        output.message = f"Files with depth higher than maximum allowed depth (>{settings.poc_max_depth}) found."
    
    return output

# git repo constraints

def _file_count_in_dir(dirpath: Path) -> int:
    file_count = 0
    
    print(f"Check file count in {dirpath}")
    
    elem_list = os.listdir(dirpath)
    for elem in elem_list:
        full_path = dirpath / elem
        if os.path.isfile(full_path):
            _, extention = os.path.splitext(full_path)
            if extention not in settings.excluded_extensions:
                file_count += 1
        else:
            if elem not in settings.excluded_dirs:
                file_count += _file_count_in_dir(full_path)
            
    return file_count

def git_repo_count_constraint(dirpath: Path) -> ConstraintOutput:
    output = ConstraintOutput(result = Result.OK, message = "ok")
    
    file_count = _file_count_in_dir(dirpath)
    
    print(file_count)
    
    if file_count > settings.poc_max_files:
        output.result = Result.FILE_LIMIT
        output.message = f"Number of files in repository exceeds the limit (>{settings.poc_max_files})"
    
    return output

def git_repo_depth_constraint(dirpath: Path) -> ConstraintOutput:
    output = ConstraintOutput(result = Result.OK, message = "ok")
    
    return output