"""Minimal stdio JSON-RPC client for solidcraft-mcp, which drives the running SolidCraft GUI.

Usage as module: g = Gui(); g.call("execute", {...}).
CLI: python -I gui.py TOOL [JSON-ARGS]   (prints the result)
"""
import json
import subprocess
import sys


class Gui:
    def __init__(self, cmd=("solidcraft-mcp",)):
        self.p = subprocess.Popen(list(cmd), stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self.n = 0
        self.rpc("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "build", "version": "1"}})
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def send(self, msg):
        self.p.stdin.write(json.dumps(msg) + "\n")
        self.p.stdin.flush()

    def rpc(self, method, params):
        self.n += 1
        self.send({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params})
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError("solidcraft-mcp closed")
            msg = json.loads(line)
            if msg.get("id") == self.n:
                if "error" in msg:
                    raise RuntimeError(msg["error"])
                return msg["result"]

    def call(self, tool, args=None):
        """Calls a tool; raises on isError. Returns the content list."""
        r = self.rpc("tools/call", {"name": tool, "arguments": args or {}})
        if r.get("isError"):
            raise RuntimeError(f"{tool} failed: {json.dumps(r.get('content'))[:3000]}")
        return r.get("content", [])

    def tools(self):
        return self.rpc("tools/list", {})["tools"]


if __name__ == "__main__":
    g = Gui()
    if sys.argv[1] == "--list":
        for t in g.tools():
            print(t["name"], json.dumps(t.get("inputSchema"))[:600])
    else:
        out = g.call(sys.argv[1], json.loads(sys.argv[2]) if len(sys.argv) > 2 else {})
        for c in out:
            print(c.get("text", c.get("type"))[:4000])
