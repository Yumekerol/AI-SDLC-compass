import os
import uuid
from datetime import datetime

from pathlib import Path
from time import sleep
from queue import Queue, ShutDown
from threading import Lock, Thread

from fastapi import UploadFile

import logging

from ..models.job import Job, JobStatus, RepoKind, URLInput
from ..models.constraint_output import Result
from ..models.zip_result import ZipResult
from ..models.clone_result import CloneResult
from ..models.scanner_mapping_output import build_scanner_output

from ..aquisition.zip_aquisition import aquire_and_validate_zip
from ..aquisition.git_aquisition import aquire_and_validate_repository

from ..config import settings

from .metrics import collect_all_metrics

logger = logging.getLogger(__name__)


MAX_QUEUED_JOBS: int = 10000

class JobHandler():
    def __init__(self):
        self.job_dict: dict[str, Job] = dict()
        self.job_queue: Queue = Queue(maxsize=MAX_QUEUED_JOBS)
        
        self.lock = Lock()
        self.thread_pool: list[Thread] | None = None
        
    def add_job(self, scan_id: str) -> None:
        job = Job(scan_id=scan_id)
        
        with self.lock:
            self.job_dict[scan_id] = job

        self.job_queue.put(scan_id)

    def add_job_zip(self, file: UploadFile) -> str:
        scan_id = uuid.uuid4().hex

        job = Job(scan_id=scan_id)
        job.repo_kind = RepoKind.ZIP
        job.input = file

        with self.lock:
            self.job_dict[scan_id] = job
    
        self.job_queue.put(scan_id)

        return scan_id

    def add_job_url(self, url: str, token: str | None = None) -> str:
        scan_id = uuid.uuid4().hex

        job = Job(scan_id=scan_id)
        job.repo_kind = RepoKind.URL
        job.input = URLInput(url=url, token=token)
        
        with self.lock:
            self.job_dict[scan_id] = job

        self.job_queue.put(scan_id)

        return scan_id
        
    def get_job(self, scan_id: str) -> Job | None:
        with self.lock:
            return self.job_dict.get(scan_id)
       
    def get_job_status(self, scan_id: str) -> JobStatus | None:
        with self.lock:
            job = self.job_dict.get(scan_id)
            return job.status if job is not None else None
        
    def init(self):
        self.thread_pool = []
        
        for i in range(0, settings.async_max_threads):
            self.thread_pool.append(Thread(target=self._worker))
        
        for t in self.thread_pool:
            t.start()
        
    def _worker(self):
        #print("Worker started")
        
        while True:
            try:
                scan_id: str = self.job_queue.get()

            except ShutDown:
                break
            except Exception as e:
                logger.error(f"Excepttion was raised in worker thread: {e}")
                break
        
            with self.lock:
                job = self.job_dict.get(scan_id)
                if not job:
                    logger.warning(f"Queued job '{scan_id}' doesn't exist.")
                    continue

                if job.status != JobStatus.QUEUED:
                    logger.warning(f"Attempted to start scan of '{scan_id}' when it was either in progress or completed.")
                    continue
                
                job.status = JobStatus.INPROGRESS
                
                self.job_dict[scan_id] = job

            aquisition: ZipResult | CloneResult | None = None

            if job.repo_kind == RepoKind.ZIP:
                try:
                    aquisition = aquire_and_validate_zip(scan_id, job.input)
                except Exception as e:
                    logger.error(f"Unhandled exception on aquire_and_validate_zip(): {e}")

                    job.status = JobStatus.FAILED
                    self.job_dict[scan_id] = job
                    continue
            if job.repo_kind == RepoKind.URL:
                try:
                    aquisition = aquire_and_validate_repository(scan_id, job.input.url, job.input.token)
                except Exception as e:
                    logger.error(f"Aquisition of repository '{scan_id}' failed: {e}")
                    
                    job.status = JobStatus.FAILED
                    self.job_dict[scan_id] = job
                    continue

            with self.lock:
                job.constraint_output = aquisition.constraint_output
                self.job_dict[scan_id] = job

            if aquisition.constraint_output.result is not Result.OK:
                logger.info(f"Aquisition failed with constraint {aquisition.constraint_output.result}")
                with self.lock:
                    job.status = JobStatus.FAILED
                    self.job_dict[scan_id] = job
                    continue

            root: Path = settings.tmp_dir / scan_id
            metrics = collect_all_metrics(root)

            url = None

            if job.repo_kind == RepoKind.URL:
                url = job.input.url
                    
            signalgroup = build_scanner_output(metrics, url, scan_id, "git")
            
            #return {"repo": clone.repo_url, "scan_id": clone.scan_id, "head_sha": clone.head_sha, "metrics": metrics}
            #return {"repo": clone.repo_url, "scan_id": clone.scan_id, "head_sha": clone.head_sha, "signalgroup": signalgroup}
            
            with self.lock:   
                job = self.job_dict.get(scan_id)
                if not job:
                    logger.warning(f"Queued job '{scan_id}' doesn't exist.")
                    continue
                
                job.status = JobStatus.COMPLETED
                job.completion_time = datetime.now()
                job.scan_result = signalgroup
                
                self.job_dict[scan_id] = job              
                
        
            
    def close(self):
        self.job_queue.shutdown()
        for t in self.thread_pool:
            t.join()
            

job_handler = JobHandler() 
        

