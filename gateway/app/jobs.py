import os
import time
import hmac
import boto3
import hashlib
from typing import Optional
from dataclasses import dataclass, asdict
from botocore.exceptions import ClientError
from app.config import settings

@dataclass
class JobRow:
    job_id: str
    status: str
    input_url: str
    output_url: Optional[str] = None
    runpod_id: Optional[str] = None
    output: Optional[dict] = None
    metrics: Optional[dict] = None
    error: Optional[str] = None
    created_at: float = time.time()
    updated_at: float = time.time()

    def to_dict(self):
        return asdict(self)
    
class Jobs:
    def __init__(self):
        self._mem: dict[str, JobRow] = {}
        self._ddb_table = None
        if settings.ddb_table:
            self._ddb = boto3.resource("dynamodb", region_name=settings.aws_region)
            self._ddb_table = self._ddb.Table(settings.ddb_table)

    def _put_ddb(self, row: JobRow):
        ttl = int(time.time()) + settings.job_ttl_seconds
        item = row.to_dict()
        item["ttl"] = ttl
        self._ddb_table.put_item(Item=item)

    def _get_ddb(self, job_id: str) -> Optional[JobRow]:
        try:
            response = self._ddb_table.get_item(Key={"job_id": job_id})
            item = response["Item"]
            if not item:
                return None
            return JobRow(**{k: item[k] for k in JobRow.__annotations__.keys() if k in item})
        except ClientError:
            return None
        
    def _update_ddb(self, job_id: str, **fields):
        row = self.__get_ddb(job_id)
        if not row:
            return
        for k, v in fields.items():
            setattr(row, k, v)
        row.updated_at = time.time()
        self._put_ddb(row)

    def create(self, input_url: str, output_url: Optional[str]) -> JobRow:
        job_id = hex(int(time.time()*1000))[2:]
        row = JobRow(job_id=job_id, status="SUBMITTED", input_url=input_url, output_url=output_url)
        if self._ddb_table:
            self._put_ddb(row)
        else:
            self._mem[job_id] = row
        return row
    
    def update(self, job_id: str, **fields):
        if self._ddb_table:
            self._update_ddb(job_id, **fields)
            return
        row = self._mem.get(job_id)
        if not row:
            return
        for k, v in fields.items():
            setattr(row, k, v)
        self.updated_at = time.time()

    def get(self, job_id: str) -> Optional[JobRow]:
        if self._ddb_table:
            return self._get_ddb(job_id)
        return self._mem.get(job_id)
    
    def mark_running(self, job_id: str, runpod_id: str | None):
        self.update(job_id, status="RUNNING", runpod_id=runpod_id)

    def mark_failed(self, job_id: str, error: str):
        self.update(job_id, status="FAILED", error=error)

    def update_from_result(self, job_id: str, ok: bool,output: dict | None, metrics: dict | None, error: str | None):
        status = {
            ok == True: "SUCCEEDED",
            ok == False: "FAILED"
        }
        self.update(job_id, status=status[True], output=output, metrics=metrics, error=error)

def sign_hmac(secret: str, msg: str) -> str:
    return hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()