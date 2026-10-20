from __future__ import annotations

import json
import logging
import uuid
import sys
import os
import stat
import shutil

from fastapi import UploadFile
from pydantic import BaseModel
from typing import Annotated
from pathlib import Path
from zipfile import ZipFile


from ..models.scanner_output import ScannerOutput
from ..models.constraint_output import ConstraintOutput, Result
from ..models.zip_result import ZipResult

from ..security.constraints import zip_file_count_constraint, zip_file_depth_constraint, zip_file_format_constraint

from .git_aquisition import cleanup_dir

from ..config import settings

logger = logging.getLogger(__name__)

def aquire_and_validate_zip(scan_id: str, filepath: Path) -> ZipResult:
    scan_folder: Path = settings.tmp_dir / scan_id
    scan_folder.mkdir(parents=True, exist_ok=True)

    result = ZipResult(scan_id=scan_id, constraint_output=ConstraintOutput(result=Result.OK, message="ok"), path=scan_folder)

    """ logger.info("format_constraint b4")
    format_constraint: ConstraintOutput = zip_file_format_constraint(file)
    logger.info("format_constraint after")
    if format_constraint.result != Result.OK:
        result.constraint_output = format_constraint
        return result """
    
    
    #filepath: Path = scan_folder / f"{scan_id}.zip"

    """ logger.info("attempt to copy file to zip")
    with open(filepath, "wb") as f:
        logger.info("read content b4")
        content = file.file.read()
        logger.info("read content after")
        f.write(content)
    logger.info("attempt to copy file to zip after") """
    
    # at this point, file is confirmed a zip, and is stored in the tmp folder, identified by a scan_id

    count_constraint: ConstraintOutput = zip_file_count_constraint(filepath)
    if count_constraint.result != Result.OK:
        try:
            cleanup_dir(scan_folder)
        except Exception as e:
            logger.error(f"Failed to remove tmp. dir. {scan_folder}. Exception raised: {e}")
        
        result.constraint_output = count_constraint
        return result
    
    depth_constraint: ConstraintOutput = zip_file_depth_constraint(filepath)
    if depth_constraint.result != Result.OK:
        try:
            cleanup_dir(scan_folder)
        except Exception as e:
            logger.error(f"Failed to remove tmp. dir. {scan_folder}. Exception raised: {e}")
        
        result.constraint_output = depth_constraint
        return result
    
    # by this point, all constraints have been checked and passed.
    # need to extract zip

    with ZipFile(filepath, "r") as zfile:
        zfile.extractall(scan_folder)

    if os.path.isfile(filepath):
        os.remove(filepath)

    else:
        logger.warning(f"Attempted to delete zip file at '{filepath}' that doesn't exist.")
    

    return result