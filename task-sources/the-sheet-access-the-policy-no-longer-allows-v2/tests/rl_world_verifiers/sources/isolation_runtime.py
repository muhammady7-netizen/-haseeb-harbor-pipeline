"""Portable, fail-closed isolation for explicitly upgraded task executors.

This file is copied into the corrected task, not injected by a worker. The
outer container remains the security boundary. The caller retains resource
monitoring and UID selection. A namespace-enabled task explicitly ships its
Bubblewrap dependency; unchanged callers retain the strict Landlock policy.
"""
from __future__ import annotations

import json
import re

PROTOCOL_VERSION = 1
_STAGES = {"resource_limits", "libseccomp", "no_new_privs", "landlock", "seccomp", "filesystem", "identity", "attestation"}
_CODES = {"capability_unavailable", "dependency_unavailable", "setup_failed", "resource_limit",
          "timeout", "malformed_attestation", "missing_attestation", "oversized_attestation"}
_KEYS = {"version", "stage", "operation", "code", "errno", "return_code"}


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate diagnostic key")
        result[key] = value
    return result


def _valid_record(value):
    return (isinstance(value, dict) and set(value) == _KEYS
            and type(value["version"]) is int and value["version"] == PROTOCOL_VERSION
            and isinstance(value["stage"], str) and value["stage"] in _STAGES
            and isinstance(value["code"], str) and value["code"] in _CODES
            and isinstance(value["operation"], str)
            and re.fullmatch(r"[a-z0-9_]{1,64}", value["operation"]) is not None
            and all(value[key] is None or type(value[key]) is int
                    and -2147483648 <= value[key] <= 2147483647
                    for key in ("errno", "return_code")))


def completion_status(status: bytes, *, child_exit_code=None, interrupted=False) -> dict | None:
    """Read only the bounded completion record on the launcher's private pipe."""
    prefix = b"NSOK\nEXIT:"
    if len(status) > 1024 or not status.startswith(prefix):
        return None
    try:
        record = json.loads(status[len(prefix):], object_pairs_hook=_unique_object)
    except (ValueError, UnicodeError, TypeError, RecursionError):
        return None
    if (not isinstance(record, dict) or set(record) != {"exit_code", "descendants"}
            or type(record["exit_code"]) is not int
            or not -64 <= record["exit_code"] <= 255
            or type(record["descendants"]) is not bool):
        return None
    code = record["exit_code"]
    expected = code if code >= 0 else 128 - code
    return record if interrupted or child_exit_code == expected else None


def attestation_error(status: bytes, *, child_exit_code=None, timed_out=False,
                      resource_limit_exceeded=False, output_limit_exceeded=False) -> str | None:
    """Only exact OK authorizes a result; never echo arbitrary child content."""
    interrupted = timed_out or resource_limit_exceeded or output_limit_exceeded
    if (status == b"OK" or completion_status(status, child_exit_code=child_exit_code,
                                            interrupted=interrupted) is not None
            or status == b"NSOK" and interrupted):
        return None
    record = None
    if len(status) <= 1024 and status.startswith(b"ERR:"):
        try:
            candidate = json.loads(status[4:], object_pairs_hook=_unique_object)
            if _valid_record(candidate):
                record = candidate
        except (ValueError, UnicodeError, TypeError, RecursionError):
            pass
    if record is None:
        code = ("oversized_attestation" if len(status) > 1024 else
                "malformed_attestation" if status else
                "resource_limit" if resource_limit_exceeded else
                "timeout" if timed_out else "missing_attestation")
        record = dict(version=PROTOCOL_VERSION, stage="attestation", operation="read_status",
                      code=code, errno=None, return_code=None)
    record["child_exit_code"] = (child_exit_code if type(child_exit_code) is int
                                 and -2147483648 <= child_exit_code <= 2147483647 else None)
    return "OBI_ISOLATION_ERROR:" + json.dumps(record, separators=(",", ":"), sort_keys=True)


def launcher_source(limits: dict, *, candidate_uid=None, candidate_gid=None, controller=False) -> str:
    """Build a standalone helper with exactly the caller's validated limits."""
    if (set(limits) != {"address_space", "processes", "file_bytes", "open_files"}
            or any(type(value) is not int or value <= 0 for value in limits.values())):
        raise ValueError("all four positive integer execution limits are required")
    identity = None
    if candidate_uid is not None or candidate_gid is not None:
        if (type(candidate_uid) is not int or type(candidate_gid) is not int
                or not 200000 <= candidate_uid < 1000000
                or not 200000 <= candidate_gid < 1000000
                or type(controller) is not bool):
            raise ValueError("namespace execution requires reserved candidate UID/GID")
        identity = dict(uid=candidate_uid, gid=candidate_gid, controller=controller)
    elif controller:
        raise ValueError("controller identity requires a reserved candidate UID/GID")
    return ("LIMITS = " + repr(limits) + "\nIDENTITY = " + repr(identity)
            + "\n" + _CHILD_SOURCE)


_CHILD_SOURCE = r'''
import ctypes
import ctypes.util
import errno
import json
import os
import platform
import resource
import sys

status_fd = -1
stage, operation = "attestation", "parse_status_fd"


def fail(code="setup_failed", return_code=None, error=None):
    record = dict(version=1, stage=stage, operation=operation, code=code,
                  errno=error, return_code=return_code)
    if status_fd >= 0:
        try:
            os.write(status_fd, b"ERR:" + json.dumps(record, separators=(",", ":")).encode())
            os.close(status_fd)
        except OSError:
            pass
    os._exit(126)


def syscall(number, *args):
    # syscall is variadic: every scalar must have the kernel's long width.
    ctypes.set_errno(0)
    return libc.syscall(ctypes.c_long(number), *[
        ctypes.c_long(arg) if isinstance(arg, int) else arg for arg in args
    ])


def checked_seccomp(result):
    # libseccomp returns negative errno values; libc's errno is unrelated.
    if result != 0:
        fail("capability_unavailable" if operation == "load_filter"
             and result == -errno.ENOSYS else "setup_failed", result, -result if result < 0 else None)


def require_outer_capabilities(status):
    """Never grant the trusted controller authority absent from its parent."""
    values = [line.partition(":")[2].strip() for line in status.splitlines()
              if line.startswith("CapEff:")]
    if (len(values) != 1 or len(values[0]) != 16
            or any(character not in "0123456789abcdefABCDEF" for character in values[0])):
        raise ValueError("unverified parent capabilities")
    retained = sum(1 << capability for capability in (1, 5, 6, 7))
    if int(values[0], 16) & retained != retained:
        raise PermissionError(errno.EPERM, "insufficient parent capabilities")


def identity_namespace_map(source, candidate, page_size):
    """Retain parent-inside IDs and each kernel mapping extent, including gaps."""
    rows = source.splitlines()
    if not 1 <= len(rows) <= 340:
        raise ValueError("invalid parent mapping size")
    extents = []
    for row in rows:
        fields = row.split()
        if (len(fields) != 3 or any(not field or any(character not in "0123456789"
                for character in field) for field in fields)):
            raise ValueError("invalid parent mapping")
        inside, outside, count = map(int, fields)
        if count <= 0 or inside + count > 4294967295 or outside + count > 4294967295:
            raise ValueError("invalid parent mapping range")
        extents.append((inside, outside, count))
    for column in (0, 1):
        ordered = sorted(extents, key=lambda extent: extent[column])
        if any(previous[column] + previous[2] > current[column]
               for previous, current in zip(ordered, ordered[1:])):
            raise ValueError("overlapping parent mappings")
    if any(not any(start <= identity < start + count for start, _, count in extents)
           for identity in (0, candidate)):
        raise ValueError("unmapped execution identity")
    # Do not merge adjacent rows: Linux requires each child extent to fit
    # within one parent extent, even when parent-inside IDs are contiguous.
    payload = "".join(str(start) + " " + str(start) + " " + str(count) + "\n"
                      for start, _, count in sorted(extents)).encode("ascii")
    if len(payload) >= page_size:
        raise ValueError("namespace mapping exceeds one kernel write")
    return payload


def namespace_exec():
    """Construct the write boundary before any target/controller code runs."""
    global stage, operation, status_fd
    import stat
    import subprocess
    from pathlib import Path

    stage, operation = "filesystem", "validate_bubblewrap"
    binary = Path("/usr/bin/bwrap")
    try:
        info = binary.lstat()
    except OSError as exc:
        fail("dependency_unavailable", error=exc.errno)
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0
            or info.st_mode & 0o6022 or not info.st_mode & 0o111):
        fail("dependency_unavailable")
    if os.geteuid() != 0:
        fail("setup_failed", error=errno.EPERM)
    operation = "verify_outer_capabilities"
    try:
        require_outer_capabilities(Path("/proc/self/status").read_text())
    except (OSError, ValueError) as exc:
        fail("setup_failed", error=getattr(exc, "errno", None))
    # Popen supplied only the status pipe and (for pytest) its private socket.
    # Keep that socket; never pass our outer status writer to Bubblewrap.
    inherited = []
    for name in os.listdir("/proc/self/fd"):
        fd = int(name)
        if fd <= 2 or fd == status_fd:
            continue
        try:
            if os.get_inheritable(fd):
                inherited.append(fd)
        except OSError:
            pass
    if len(inherited) > 1:
        fail("setup_failed")
    child_status_read, child_status_write = os.pipe()
    info_read, info_write = os.pipe()
    block_read, block_write = os.pipe()
    process = None
    descriptors = {child_status_read, child_status_write, info_read, info_write,
                   block_read, block_write}
    def close(fd):
        if fd in descriptors:
            descriptors.remove(fd)
            os.close(fd)
    def read_bounded(fd, limit):
        data = bytearray()
        while len(data) <= limit:
            block = os.read(fd, limit + 1 - len(data))
            if not block:
                return bytes(data)
            data.extend(block)
        raise ValueError("oversized setup record")
    try:
        mappings = {}
        for mapping, candidate in (("uid_map", IDENTITY["uid"]),
                                   ("gid_map", IDENTITY["gid"])):
            operation = "read_" + mapping
            mappings[mapping] = identity_namespace_map(
                Path("/proc/self", mapping).read_text(), candidate, os.sysconf("SC_PAGESIZE")
            )
        cwd = os.getcwd()
        args = [str(binary), "--unshare-user", "--unshare-pid", "--unshare-ipc", "--as-pid-1", "--die-with-parent",
                "--userns-block-fd", str(block_read), "--info-fd", str(info_write),
                "--uid", "0", "--gid", "0", "--cap-drop", "ALL"]
        for capability in ("CAP_SETUID", "CAP_SETGID", "CAP_DAC_OVERRIDE", "CAP_KILL",
                           "CAP_SYS_ADMIN", "CAP_SETPCAP"):
            args += ["--cap-add", capability]
        args += ["--ro-bind", "/", "/", "--proc", "/proc", "--remount-ro", "/proc",
                 "--tmpfs", "/sys", "--remount-ro", "/sys", "--tmpfs", "/dev"]
        for device in ("null", "zero", "random", "urandom"):
            args += ["--dev-bind", "/dev/" + device, "/dev/" + device]
        args += ["--symlink", "/proc/self/fd", "/dev/fd",
                 "--symlink", "/proc/self/fd/0", "/dev/stdin",
                 "--symlink", "/proc/self/fd/1", "/dev/stdout",
                 "--symlink", "/proc/self/fd/2", "/dev/stderr",
                 "--remount-ro", "/dev", "--bind", cwd, cwd, "--chdir", cwd,
                 "--", sys.executable, "-I", os.path.abspath(__file__),
                 str(child_status_write), str(cpu_seconds), "--obi-namespace-ready",
                 *sys.argv[1:]]
        operation = "set_subreaper"
        if libc.prctl(36, 1, 0, 0, 0) != 0:
            fail(error=ctypes.get_errno())
        operation = "start_bubblewrap"
        process = subprocess.Popen(args, pass_fds=(*inherited, child_status_write,
                                                   info_write, block_read))
        close(child_status_write); close(info_write); close(block_read)
        operation = "read_namespace_identity"
        record = json.loads(read_bounded(info_read, 4096))
        close(info_read)
        child_pid = record.get("child-pid")
        if type(child_pid) is not int or child_pid <= 0:
            raise ValueError("invalid namespace identity")
        # Use privileged parent maps so setgroups remains usable by the trusted
        # controller's Popen(user=..., group=..., extra_groups=()).
        # Preserve already-mapped inode owners so the trusted controller can
        # read private uploaded tests. The candidate keeps the same kernel IDs.
        for mapping, payload in mappings.items():
            operation = "write_" + mapping
            with Path("/proc", str(child_pid), mapping).open("wb", buffering=0) as handle:
                if handle.write(payload) != len(payload):
                    raise OSError(errno.EIO, "incomplete namespace mapping")
        operation = "release_namespace"
        os.write(block_write, b"1"); close(block_write)
        operation = "read_inner_attestation"
        prefix = os.read(child_status_read, 2)
        if prefix == b"OK":
            # Tell the parent confinement completed before target execution.
            # Keep the pipe open for the separate trusted PID 1 completion record.
            os.write(status_fd, b"NSOK")
            completion = read_bounded(child_status_read, 1000)
            os.write(status_fd, completion)
        else:
            inner = prefix + read_bounded(child_status_read, 1000)
            if not inner:
                result = process.wait()
                fail("setup_failed", return_code=result)
            # A child setup error precedes PID 1's completion metadata; it must
            # retain its original structured cause, and never authorizes a grade.
            os.write(status_fd, inner.split(b"\nEXIT:", 1)[0])
        close(child_status_read)
        os.close(status_fd); status_fd = -1
        result = process.wait()
        # Reap namespace helpers before the outer executor checks our group.
        while True:
            try:
                os.waitpid(-1, 0)
            except ChildProcessError:
                break
        os._exit(result if result >= 0 else 128 - result)
    except BaseException as exc:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        fail("setup_failed", error=getattr(exc, "errno", None))
    finally:
        for fd in tuple(descriptors):
            close(fd)


try:
    status_fd = int(sys.argv.pop(1))
    stage, operation = "resource_limits", "parse_cpu_limit"
    cpu_seconds = max(1, int(sys.argv.pop(1)))
    namespace_ready = bool(sys.argv[1:] and sys.argv[1] == "--obi-namespace-ready")
    if namespace_ready:
        sys.argv.pop(1)
        if IDENTITY is None:
            fail("setup_failed")
    for name, resource_id, soft, hard in (
        ("address_space", resource.RLIMIT_AS, LIMITS["address_space"], LIMITS["address_space"]),
        ("processes", resource.RLIMIT_NPROC, LIMITS["processes"], LIMITS["processes"]),
        ("file_bytes", resource.RLIMIT_FSIZE, LIMITS["file_bytes"], LIMITS["file_bytes"]),
        ("open_files", resource.RLIMIT_NOFILE, LIMITS["open_files"], LIMITS["open_files"]),
        ("cpu", resource.RLIMIT_CPU, cpu_seconds, cpu_seconds + 1),
        ("core", resource.RLIMIT_CORE, 0, 0),
    ):
        operation = "set_" + name
        resource.setrlimit(resource_id, (soft, hard))

    stage, operation = "libseccomp", "find_library"
    library_name = ctypes.util.find_library("seccomp")
    if not library_name:
        fail("dependency_unavailable")
    operation = "load_library"
    library = ctypes.CDLL(library_name, use_errno=True)
    library.seccomp_init.argtypes = [ctypes.c_uint32]
    library.seccomp_init.restype = ctypes.c_void_p
    library.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    library.seccomp_syscall_resolve_name.restype = ctypes.c_int
    class ScmpArgCmp(ctypes.Structure):
        _fields_ = [("arg", ctypes.c_uint), ("op", ctypes.c_uint),
                    ("datum_a", ctypes.c_uint64), ("datum_b", ctypes.c_uint64)]
    library.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    library.seccomp_rule_add.restype = ctypes.c_int
    library.seccomp_rule_add_array.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int,
                                             ctypes.c_uint, ctypes.POINTER(ScmpArgCmp)]
    library.seccomp_rule_add_array.restype = ctypes.c_int
    library.seccomp_load.argtypes = [ctypes.c_void_p]
    library.seccomp_load.restype = ctypes.c_int
    library.seccomp_release.argtypes = [ctypes.c_void_p]
    library.seccomp_release.restype = None

    stage, operation = "no_new_privs", "prctl"
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
    libc.prctl.restype = ctypes.c_int
    libc.syscall.restype = ctypes.c_long
    ctypes.set_errno(0)
    result = libc.prctl(38, 1, 0, 0, 0)
    if result != 0:
        fail(return_code=result, error=ctypes.get_errno())

    if not namespace_ready:
        stage, operation = "landlock", "architecture"
        if platform.machine().lower() not in {"x86_64", "amd64", "aarch64", "arm64"}:
            fail("capability_unavailable")
        class RulesetAttr(ctypes.Structure):
            _fields_ = [("handled_access_fs", ctypes.c_uint64)]
        class PathBeneathAttr(ctypes.Structure):
            _fields_ = [("allowed_access", ctypes.c_uint64), ("parent_fd", ctypes.c_int32)]
        operation = "query_abi"
        version = syscall(444, 0, 0, 1)
        if version < 3:
            error = ctypes.get_errno() if version < 0 else None
            unavailable = version >= 0 or error in {errno.ENOSYS, errno.EOPNOTSUPP, errno.ENOMSG}
            if unavailable and IDENTITY is not None:
                namespace_exec()
            fail("capability_unavailable" if unavailable else "setup_failed", version, error)
        # ABI 3 is mandatory: earlier versions cannot deny truncate(2) outside the workspace.
        rights = sum(1 << bit for bit in (1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14))
        ruleset = RulesetAttr(rights)
        operation = "create_ruleset"
        ruleset_fd = syscall(444, ctypes.byref(ruleset), ctypes.sizeof(ruleset), 0)
        if ruleset_fd < 0:
            fail(return_code=ruleset_fd, error=ctypes.get_errno())
        operation = "open_workspace"
        parent_fd = os.open(os.getcwd(), os.O_PATH | os.O_CLOEXEC)
        try:
            rule = PathBeneathAttr(rights, parent_fd)
            operation = "add_rule"
            result = syscall(445, ruleset_fd, 1, ctypes.byref(rule), 0)
            if result != 0:
                fail(return_code=result, error=ctypes.get_errno())
            operation = "restrict_self"
            result = syscall(446, ruleset_fd, 0)
            if result != 0:
                fail(return_code=result, error=ctypes.get_errno())
        finally:
            os.close(parent_fd)
            os.close(ruleset_fd)

    if namespace_ready:
        # Bubblewrap's loopback configuration is not supported by every runtime.
        # Only this trusted prelude temporarily retains the two setup caps;
        # create the private network namespace, then irreversibly drop them
        # before forking or executing any target/controller code.
        stage, operation = "filesystem", "unshare_network"
        libc.unshare.argtypes = [ctypes.c_int]
        libc.unshare.restype = ctypes.c_int
        if libc.unshare(0x40000000) != 0:
            fail(error=ctypes.get_errno())
        operation = "drop_setup_capability_bounds"
        for capability in (21, 8):  # CAP_SYS_ADMIN, CAP_SETPCAP
            if libc.prctl(24, capability, 0, 0, 0) != 0:
                fail(error=ctypes.get_errno())
            if libc.prctl(23, capability, 0, 0, 0) != 0:
                fail()
        operation = "clear_ambient_capabilities"
        if libc.prctl(47, 4, 0, 0, 0) != 0:
            fail(error=ctypes.get_errno())
        class CapHeader(ctypes.Structure):
            _fields_ = [("version", ctypes.c_uint32), ("pid", ctypes.c_int)]
        class CapData(ctypes.Structure):
            _fields_ = [("effective", ctypes.c_uint32), ("permitted", ctypes.c_uint32),
                        ("inheritable", ctypes.c_uint32)]
        header = CapHeader(0x20080522, 0)
        retained = sum(1 << capability for capability in (1, 5, 6, 7))
        capabilities = (CapData * 2)(CapData(retained, retained, 0), CapData(0, 0, 0))
        libc.capset.argtypes = [ctypes.POINTER(CapHeader), ctypes.POINTER(CapData)]
        libc.capset.restype = ctypes.c_int
        libc.capget.argtypes = [ctypes.POINTER(CapHeader), ctypes.POINTER(CapData)]
        libc.capget.restype = ctypes.c_int
        operation = "drop_setup_capabilities"
        if libc.capset(ctypes.byref(header), capabilities) != 0:
            fail(error=ctypes.get_errno())
        operation = "verify_target_capabilities"
        observed = (CapData * 2)()
        if libc.capget(ctypes.byref(header), observed) != 0:
            fail(error=ctypes.get_errno())
        if (observed[0].effective != retained or observed[0].permitted != retained
                or observed[0].inheritable != 0 or observed[1].effective != 0
                or observed[1].permitted != 0 or observed[1].inheritable != 0):
            fail()

    stage, operation = "seccomp", "initialize"
    ctypes.set_errno(0)
    context = library.seccomp_init(0x7FFF0000)
    if not context:
        fail(error=ctypes.get_errno() or None)
    deny = 0x00050000 | errno.EPERM
    operation = "resolve_socket"
    socket_number = library.seccomp_syscall_resolve_name(b"socket")
    socketcall_number = library.seccomp_syscall_resolve_name(b"socketcall")
    if socket_number < 0:
        fail(return_code=socket_number)
    operation = "rule_socket"
    comparison = ScmpArgCmp(0, 1, 1, 0)  # arg0 != AF_UNIX
    checked_seccomp(library.seccomp_rule_add_array(context, deny, socket_number, 1, ctypes.byref(comparison)))
    if socketcall_number >= 0:
        operation = "rule_socketcall"
        checked_seccomp(library.seccomp_rule_add(context, deny, socketcall_number, 0))
    operation = "resolve_clone"
    clone_number = library.seccomp_syscall_resolve_name(b"clone")
    clone3_number = library.seccomp_syscall_resolve_name(b"clone3")
    if clone_number < 0 or clone3_number < 0:
        fail()
    operation = "rule_clone_namespace"
    for flag in (0x00020000, 0x02000000, 0x04000000, 0x08000000, 0x10000000, 0x20000000, 0x40000000):
        comparison = ScmpArgCmp(0, 7, flag, flag)
        checked_seccomp(library.seccomp_rule_add_array(context, deny, clone_number, 1, ctypes.byref(comparison)))
    operation = "rule_clone3"
    checked_seccomp(library.seccomp_rule_add(context, 0x00050000 | errno.ENOSYS, clone3_number, 0))
    for name in (b"io_uring_setup", b"io_uring_enter", b"io_uring_register", b"ptrace",
                 b"process_vm_readv", b"process_vm_writev", b"bpf", b"perf_event_open",
                 b"mount", b"umount2", b"setns", b"unshare", b"chroot", b"pivot_root",
                 b"open_tree", b"move_mount", b"fsopen", b"fsconfig", b"fsmount",
                 b"fspick", b"mount_setattr", b"open_by_handle_at", b"pidfd_getfd"):
        operation = "resolve_" + name.decode()
        number = library.seccomp_syscall_resolve_name(name)
        if number < 0:
            fail(return_code=number)
        operation = "rule_" + name.decode()
        checked_seccomp(library.seccomp_rule_add(context, deny, number, 0))
    if namespace_ready:
        # A read-only mount does not constrain writable FDs imported from an
        # outside pathname Unix socket. Ordinary Unix byte-stream IPC remains.
        for name in (b"recvmsg", b"recvmmsg"):
            operation = "resolve_" + name.decode()
            number = library.seccomp_syscall_resolve_name(name)
            if number < 0:
                fail(return_code=number)
            operation = "rule_" + name.decode()
            checked_seccomp(library.seccomp_rule_add(context, deny, number, 0))
    operation = "load_filter"
    checked_seccomp(library.seccomp_load(context))
    library.seccomp_release(context)
    if namespace_ready:
        # PID 1 supervises the target, retaining only the policy's minimal caps.
        # Kernel namespace teardown also kills children which called setsid().
        stage, operation = "identity", "protect_supervisor"
        if libc.prctl(4, 0, 0, 0, 0) != 0:
            fail(error=ctypes.get_errno())
        stage, operation = "identity", "fork_target"
        target_pid = os.fork()
        if target_pid:
            for descriptor in os.listdir("/proc/self/fd"):
                fd = int(descriptor)
                if fd > 2 and fd != status_fd:
                    try:
                        os.close(fd)
                    except OSError:
                        pass
            _, target_status = os.waitpid(target_pid, 0)
            live = False
            for name in os.listdir("/proc"):
                if name.isdigit() and int(name) != os.getpid():
                    # Even a zombie proves an unreaped descendant. Ignoring it
                    # could miss a child forked after this directory snapshot.
                    live = True
            code = os.waitstatus_to_exitcode(target_status)
            os.write(status_fd, b"\nEXIT:" + json.dumps(
                dict(exit_code=code, descendants=live), separators=(",", ":")
            ).encode())
            os.close(status_fd)
            os._exit(code if code >= 0 else 128 - code)
    if IDENTITY is not None:
        stage, operation = "identity", "clear_groups"
        os.setgroups([])
        if not IDENTITY["controller"]:
            operation = "set_gid"
            os.setgid(IDENTITY["gid"])
            operation = "set_uid"
            os.setuid(IDENTITY["uid"])
            os.umask(0o077)
    stage, operation = "attestation", "write_status"
    if os.write(status_fd, b"OK") != 2:
        fail()
    os.close(status_fd)
    status_fd = -1
except BaseException as exc:
    fail("resource_limit" if stage == "resource_limits" else "setup_failed",
         error=getattr(exc, "errno", None))
os.execv(sys.argv[1], sys.argv[1:])
'''
