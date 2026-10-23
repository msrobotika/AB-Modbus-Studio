#!/usr/bin/env python3
"""Smoke locally BUILT candidate binary (never claim a release was published)."""
import argparse
import json
from pathlib import Path
import tempfile

from verify_published_release import run_binary, smoke_hmi

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--binary",type=Path,required=True)
    opts=p.parse_args()
    binary=opts.binary.resolve()
    if not binary.is_file():raise RuntimeError("No existe ejecutable candidato")
    meta=binary.parent/"BUILD-INFO.json"
    if not meta.is_file():raise RuntimeError("Falta información reproducible de build")
    data=json.loads(meta.read_text(encoding="utf-8"))
    if data.get("application")!="0.1.0" or data.get("self_test")!="passed":
        raise RuntimeError("Build no acreditó autoprueba/version del motor")
    test=json.loads(run_binary(binary,"--self-test").splitlines()[-1])
    if test != {"ok":True,"version":"0.1.0","functions":[1,2,3,4]}:
        raise RuntimeError("La candidata no pasa autoprueba")
    with tempfile.TemporaryDirectory(prefix="abmodbus-build-qa-",ignore_cleanup_errors=True) as temp:
        web=smoke_hmi(binary,Path(temp))
    print(json.dumps({"status":"CANDIDATE_QA_ONLY","binary":binary.name,
                      "source":"CURRENT_BRANCH_NOT_RELEASE","self_test":"PASS",
                      "build_info":data,"hmi":web},ensure_ascii=False))

if __name__=="__main__":main()
