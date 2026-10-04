"""Execute retained repository helpers in private, source-bound namespaces.

Callers authenticate the complete buffer map before creating this loader.
Canonical import caches and interpreter builtins are never replaced.
"""

from __future__ import annotations

import ast
import builtins
from collections.abc import MutableMapping
from importlib.util import resolve_name
from pathlib import Path
import sys
from types import CodeType, ModuleType
from typing import Any
from weakref import WeakSet

# A nested invocation can load this stdlib-only helper through its parent's
# private importer. Each registry still owns registrations in the actual
# runtime, so an inner close removes its own modules immediately.
sys = getattr(sys, "_b3_authenticated_runtime_sys", sys)


class _OwnedModules(MutableMapping):
    """Expose original cache reads; keep helper writes and deletions private."""

    def __init__(self, registry):
        self.registry = registry
        self.aliases: dict[str, ModuleType] = {}

    def __getitem__(self, key):
        if key in self.aliases:
            return self.aliases[key]
        return sys.modules[key]

    def __setitem__(self, key, value):
        self.registry.budget.check()
        if not isinstance(key, str) or not isinstance(value, ModuleType):
            raise ValueError("Private helper registration requires a module and string identity")
        if value.__name__ not in self.registry.module_names or sys.modules.get(value.__name__) is not value:
            private = f"_b3_authenticated_{id(self.registry)}_clone_{len(self.registry.module_names)}"
            value.__name__ = private
            sys.modules[private] = value
            self.registry.module_names.append(private)
        self.aliases[key] = value

    def __delitem__(self, key):
        # Canonical/pre-existing runtime entries cannot be deleted by helpers.
        del self.aliases[key]

    def __iter__(self):
        return iter(dict.fromkeys([*sys.modules, *self.aliases]))

    def __len__(self):
        return len(set(sys.modules) | set(self.aliases))

    def pop(self, key, default=None):
        return self.aliases.pop(key, default)


class AuthenticatedHelpers:
    """Own authenticated imports and nested execution for one bounded call."""

    def __init__(self, root: Path, buffers: dict[Path, bytes], budget: Any):
        self.root, self.budget = root, budget
        self.buffers = dict(buffers)
        self.module_names: list[str] = []
        self.modules: dict[str, ModuleType] = {}
        self.states: dict[str, str] = {}
        self.paths: dict[str, Path] = {}
        self.compiled: WeakSet[CodeType] = WeakSet()
        self.owned_modules = _OwnedModules(self)
        self.sys_facade = ModuleType("sys")
        self.sys_facade.__dict__.update(vars(sys))
        self.sys_facade.__dict__["modules"] = self.owned_modules
        self.sys_facade.__dict__["_b3_authenticated_runtime_sys"] = sys
        self._ordinary_import = builtins.__import__
        self._ordinary_compile, self._ordinary_exec = builtins.compile, builtins.exec
        self.guarded_builtins = dict(vars(builtins))
        self.guarded_builtins.update(__import__=self._import, compile=self._compile, exec=self._exec)
        for path, data in self.buffers.items():
            if not isinstance(path, Path) or type(data) is not bytes:
                raise ValueError("Authenticated helper map requires exact retained byte buffers")
            identity = self._identity(path)
            if identity in self.paths and self.paths[identity] != path:
                raise ValueError("Conflicting authenticated repository module identities")
            self.paths[identity] = path

    def _identity(self, path: Path) -> str:
        for base, prefix in (
            (self.root / "scripts", "scripts"),
            (self.root / "src/transcriptformer", "transcriptformer"),
        ):
            if path.is_relative_to(base) and path.suffix == ".py":
                parts = list(path.relative_to(base).with_suffix("").parts)
                if parts[-1] == "__init__":
                    parts.pop()
                return ".".join([prefix, *parts])
        raise ValueError("Helper source is outside the bound repository namespaces")

    def _allocate(self, identity: str) -> ModuleType:
        self.budget.check()
        if identity in self.modules:
            return self.modules[identity]
        path = self.paths.get(identity)
        if path is None and identity != "scripts":
            raise ValueError("Repository helper import is absent from the authenticated closure: " + identity)
        private = f"_b3_authenticated_{id(self)}_{identity.replace('.', '_')}"
        module = ModuleType(private)
        is_package = identity == "scripts" or (path is not None and path.name == "__init__.py")
        module.__package__ = identity if is_package else identity.rpartition(".")[0]
        module.__dict__["__builtins__"] = self.guarded_builtins
        if path is not None:
            module.__file__ = str(path)
        if is_package:
            module.__path__ = []
        self.modules[identity], self.states[identity] = module, "allocated"
        sys.modules[private] = module
        self.module_names.append(private)
        if "." in identity:
            parent, _, leaf = identity.rpartition(".")
            setattr(self._module(parent), leaf, module)
        if path is None:
            self.states[identity] = "ready"
        return module

    def _module(self, identity: str) -> ModuleType:
        module = self._allocate(identity)
        if self.states[identity] == "failed":
            raise ValueError("Authenticated repository helper initialization previously failed")
        if self.states[identity] == "allocated":
            path = self.paths[identity]
            self._exec(self._compile(self.buffers[path], str(path), "exec"), module.__dict__)
        return module

    def load(self, path: Path) -> ModuleType:
        if path not in self.buffers:
            raise ValueError("Helper source is absent from the authenticated closure")
        return self._module(self._identity(path))

    def _import(self, name, globals=None, locals=None, fromlist=(), level=0):
        self.budget.check()
        if level:
            package = (globals or {}).get("__package__")
            if not isinstance(package, str) or not package:
                raise ValueError("Relative helper import has no authenticated package")
            name = resolve_name("." * level + name, package)
        if name == "sys":
            return self.sys_facade
        if name in {"scripts", "transcriptformer"} or name.startswith(("scripts.", "transcriptformer.")):
            module = self._module(name)
            for leaf in fromlist or ():
                if leaf == "*" or hasattr(module, leaf):
                    continue
                child = name + "." + leaf
                if child in self.paths:
                    setattr(module, leaf, self._module(child))
                else:
                    raise ValueError("Requested repository helper member is unbound or partially initialized: " + child)
            return module if fromlist else self._module(name.partition(".")[0])
        return self._ordinary_import(name, globals, locals, fromlist, 0)

    def _compile(self, source, filename, mode, *args, **kwargs):
        self.budget.check()
        path = Path(filename)
        if path in self.buffers:
            # The frozen publisher selects three AST functions only after its
            # separate fixed engine hash check. Preserve that verified seam.
            if not isinstance(source, ast.AST) and (type(source) is not bytes or source != self.buffers[path]):
                raise ValueError("Helper compile buffer differs from authenticated retained bytes")
        elif path.is_relative_to(self.root / "scripts") or path.is_relative_to(self.root / "src/transcriptformer"):
            raise ValueError("Helper compile source is outside the authenticated closure")
        code = self._ordinary_compile(source, filename, mode, *args, **kwargs)
        if isinstance(code, CodeType):
            self.compiled.add(code)
        return code

    def _exec(self, code, globals=None, locals=None, *, closure=None):
        self.budget.check()
        if not isinstance(code, CodeType) or code not in self.compiled:
            raise ValueError("Private helper execution requires authenticated compiled code")
        if globals is None:
            frame = sys._getframe(1)
            globals = frame.f_globals
            if locals is None:
                locals = frame.f_locals
        globals["__builtins__"] = self.guarded_builtins
        identity = next((key for key, module in self.modules.items() if module.__dict__ is globals), None)
        if identity is not None:
            if self.states[identity] == "ready":
                return None
            if self.states[identity] == "executing":
                raise ValueError("Recursive helper body execution is unavailable")
            self.states[identity] = "executing"
        try:
            if closure is None:
                result = self._ordinary_exec(code, globals, locals)
            else:
                result = self._ordinary_exec(code, globals, locals, closure=closure)
        except BaseException:
            if identity is not None:
                self.states[identity] = "failed"
            raise
        if identity is not None:
            self.states[identity] = "ready"
        self.budget.check()
        return result

    def role_factory(self, roles: dict[str, Path]):
        """Reuse imports only for the frozen legacy role loop, never clones."""

        def factory(name, doc=None):
            if name.startswith("_paged_native_application_"):
                role = name.rpartition("_")[2]
                if role not in roles:
                    raise ValueError("Unknown original private helper role")
                path = roles[role]
                if path not in self.buffers:
                    raise ValueError("Original private helper role is outside its authenticated closure")
                return self._allocate(self._identity(path))
            return ModuleType(name, doc)

        return factory

    def close(self) -> None:
        for name in self.module_names:
            sys.modules.pop(name, None)
        self.module_names.clear()
        self.modules.clear()
        self.states.clear()
        self.buffers.clear()
        self.compiled.clear()
        self.owned_modules.aliases.clear()
