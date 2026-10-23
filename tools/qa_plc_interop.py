#!/usr/bin/env python3
"""True cross-project integration: AB-PLC VirtualPLC ↔ AB-Modbus Studio FC01/03.
No simulated network responses: Node owns the virtual CPU, HTTP and TCP sockets.
Only localhost. NEVER connects to hardware, never uses industrial write APIs.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ab_modbus.client import ReadClient

NODE_SERVER = r"""
import { startSuiteLive } from './src/suite-live-server.js';
const service=await startSuiteLive({httpPort:0,modbusPort:0,
  scenario:'conveyor',autoRun:true,clock:false});
console.log(JSON.stringify({url:service.url,modbusPort:service.modbusPort}));
const shutdown=()=>service.close().then(()=>process.exit(0));
process.on('SIGTERM',shutdown);
process.on('SIGINT',shutdown);
"""

def assert_safe_addr(url: str, port: int) -> str:
    from urllib.parse import urlsplit,parse_qs
    parsed=urlsplit(url)
    assert parsed.scheme=="http" and parsed.hostname=="127.0.0.1"
    assert 1 <= parsed.port <= 65535
    token=parse_qs(parsed.fragment).get("suite",[""])[0]
    assert len(token)==64 and all(x in "0123456789abcdef" for x in token)
    assert type(port) is int and 1<=port<=65535
    return token

def http_json(base, token, route, command=None):
    payload=None if command is None else json.dumps(command).encode()
    request=Request(base+route,method="GET" if payload is None else "POST",
        data=payload,headers={"Authorization":"Bearer "+token,
          **({"Content-Type":"application/json"} if payload is not None else {})})
    with urlopen(request,timeout=8) as response:
        assert response.status==200
        return json.load(response)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--plc-repo",required=True,type=Path)
    a=parser.parse_args()
    project=a.plc_repo.resolve()
    assert (project/"src"/"suite-live-server.js").is_file(), "Falta la fuente PLC original"
    with tempfile.TemporaryDirectory(prefix="abmodbus-suite-interop-") as temp:
        output=Path(temp)/"plc-runtime-output.txt"
        with output.open("w+",encoding="utf-8",errors="replace") as log:
            proc=subprocess.Popen(["node","--input-type=module","-e",NODE_SERVER],
                   cwd=project,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
            try:
                info=None
                end=time.monotonic()+20
                while time.monotonic()<end:
                    if proc.poll() is not None:
                        raise RuntimeError("AB-PLC Simulator se detuvo al iniciar")
                    log.seek(0)
                    for line in log.read().splitlines():
                        try:
                            payload=json.loads(line)
                            if "url" in payload:
                                info=payload
                                break
                        except json.JSONDecodeError:
                            continue
                    if info:break
                    time.sleep(.1)
                if not info:raise RuntimeError("Sin respuesta de VirtualPLC/Suite Live")
                token=assert_safe_addr(info["url"], info["modbusPort"])
                url=info["url"].split("/#",1)[0]
                tcp_port=info["modbusPort"]
                try:
                    http_json(url,"wrong","/api/live/state")
                    raise AssertionError("API HMI aceptó token inválido")
                except HTTPError as e:
                    assert e.code==401, "Error inesperado sin sesión"
                # Advance the REAL shared CPU via its authenticated local HMI API.
                for _ in range(8):
                    http_json(url,token,"/api/live/command",{"command":"step"})
                state=http_json(url,token,"/api/live/state")["snapshot"]
                client=ReadClient()
                coils=client.read(port=tcp_port,function=1,address=0,count=3)["values"]
                registers=client.read(port=tcp_port,function=3,address=0,count=5)["values"]
                assert coils[0] == int(bool(state["cpu"]["outputs"].get("Q0.0",False)))
                assert registers[0] == state["scan"], "FC03 no comparte el scan de la CPU"
                assert registers[1] == state["simulatedMs"]//100
                # Fault is set on the actual simulator; Modbus must still reflect
                # this same CPU, never a second browser-specific instance.
                http_json(url,token,"/api/live/command",
                          {"command":"fault","fault":"jam","value":True})
                http_json(url,token,"/api/live/command",{"command":"step"})
                after=http_json(url,token,"/api/live/state")["snapshot"]
                actual=client.read(port=tcp_port,function=1,address=0,count=3)["values"]
                scan=client.read(port=tcp_port,function=3,address=0,count=2)["values"]
                assert after["faults"]["jam"] is True
                assert actual[0]==int(bool(after["cpu"]["outputs"].get("Q0.0",False)))
                assert scan[0]==after["scan"]
                assert scan[0]>registers[0]
                print(json.dumps({"result":"PASS",
                  "origin":"AB-PLC-Simulator actual VirtualPLC server (pinned SHA)",
                  "consumer":"AB-Modbus Studio actual ReadClient",
                  "functions":["FC01","FC03"],"shared_cpu":True,
                  "scan_before":state["scan"],"scan_after":after["scan"],
                  "fault_injected":"jam (virtual only)","token_logged":False}))
            finally:
                proc.terminate()
                try: proc.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    proc.kill();proc.wait(timeout=8)

if __name__=="__main__":
    main()
