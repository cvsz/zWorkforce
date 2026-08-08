from __future__ import annotations
import ast, json, operator, subprocess, urllib.parse, urllib.request
TOOL_SCHEMAS=[
{"type":"function","function":{"name":"calculator","description":"Evaluate basic arithmetic.","parameters":{"type":"object","properties":{"expression":{"type":"string"}},"required":["expression"]}}},
{"type":"function","function":{"name":"workspace_list","description":"List workspace files.","parameters":{"type":"object","properties":{"path":{"type":"string"}}}}},
{"type":"function","function":{"name":"workspace_read","description":"Read a UTF-8 workspace file.","parameters":{"type":"object","properties":{"path":{"type":"string"},"max_bytes":{"type":"integer"}},"required":["path"]}}},
{"type":"function","function":{"name":"http_get","description":"GET an allowlisted URL.","parameters":{"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}}},
{"type":"function","function":{"name":"shell_exec","description":"Run an allowlisted command; disabled by default.","parameters":{"type":"object","properties":{"command":{"type":"string"},"args":{"type":"array","items":{"type":"string"}}},"required":["command"]}}},
{"type":"function","function":{"name":"agent_delegate","description":"Delegate a bounded subtask.","parameters":{"type":"object","properties":{"agent_id":{"type":"string"},"prompt":{"type":"string"},"mutating":{"type":"boolean"}},"required":["agent_id","prompt"]}}}
]
class ToolError(RuntimeError): pass
class ToolExecutor:
    OPS={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.FloorDiv:operator.floordiv,ast.Mod:operator.mod,ast.Pow:operator.pow,ast.USub:operator.neg,ast.UAdd:operator.pos}
    def __init__(self,settings): self.settings=settings; self.root=settings.workspace_root.resolve()
    def _safe_path(self,raw):
        p=(self.root/raw).resolve()
        if p!=self.root and self.root not in p.parents: raise ToolError("path escapes workspace root")
        return p
    def execute(self,name,args):
        if name=="calculator": return self._calc(str(args.get("expression","")))
        if name=="workspace_list":
            p=self._safe_path(str(args.get("path",".")))
            if not p.is_dir(): raise ToolError("directory not found")
            return [{"name":x.name,"type":"dir" if x.is_dir() else "file"} for x in sorted(p.iterdir(),key=lambda x:x.name)[:500]]
        if name=="workspace_read":
            p=self._safe_path(str(args.get("path",""))); limit=max(1,min(int(args.get("max_bytes",65536)),262144))
            if not p.is_file(): raise ToolError("file not found")
            return p.read_bytes()[:limit].decode("utf-8",errors="replace")
        if name=="http_get": return self._http_get(str(args.get("url","")))
        if name=="shell_exec": return self._shell(str(args.get("command","")),[str(x) for x in args.get("args",[])])
        raise ToolError(f"unknown tool: {name}")
    def _calc(self,expression):
        def walk(node):
            if isinstance(node,ast.Expression): return walk(node.body)
            if isinstance(node,ast.Constant) and isinstance(node.value,(int,float)): return node.value
            if isinstance(node,ast.BinOp) and type(node.op) in self.OPS: return self.OPS[type(node.op)](walk(node.left),walk(node.right))
            if isinstance(node,ast.UnaryOp) and type(node.op) in self.OPS: return self.OPS[type(node.op)](walk(node.operand))
            raise ToolError("unsupported calculator expression")
        if len(expression)>200: raise ToolError("expression too long")
        return walk(ast.parse(expression,mode="eval"))
    def _http_get(self,url):
        p=urllib.parse.urlparse(url)
        if p.scheme not in {"http","https"} or not p.hostname: raise ToolError("invalid URL")
        if not self.settings.http_allowlist or not any(p.hostname==h or p.hostname.endswith("."+h) for h in self.settings.http_allowlist): raise ToolError("host is not allowlisted")
        req=urllib.request.Request(url,headers={"User-Agent":"zWorkforce/1.0"})
        with urllib.request.urlopen(req,timeout=self.settings.tool_timeout_seconds) as resp:
            data=resp.read(262144); return {"status":resp.status,"content_type":resp.headers.get("Content-Type",""),"body":data.decode("utf-8",errors="replace")}
    def _shell(self,command,args):
        if not self.settings.shell_enabled: raise ToolError("shell tool is disabled")
        if command not in self.settings.shell_allowlist: raise ToolError("command is not allowlisted")
        if len(args)>64 or any(len(a)>4096 for a in args): raise ToolError("shell arguments exceed limits")
        p=subprocess.run([command,*args],cwd=self.root,capture_output=True,text=True,timeout=self.settings.tool_timeout_seconds,shell=False)
        return {"exit_code":p.returncode,"stdout":p.stdout[-65536:],"stderr":p.stderr[-65536:]}
