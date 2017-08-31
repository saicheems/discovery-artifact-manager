"""Contains convenience functions that wrap `subprocess.Popen`."""
import shlex
from subprocess import PIPE, Popen

class CallError(Exception):
    """Represents a call error."""
    pass


def _call(cmd, **kwargs):
    proc = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE, **kwargs)
    stdoutdata, stderrdata = proc.communicate()
    return (proc.returncode,
            stdoutdata.decode('utf-8'),
            stderrdata.decode('utf-8'))


def call(cmd, **kwargs):
    """A convenient version of `subprocess.call`.

    Similar in behavior to `subprocess.call`, but accepts the args as a single
    string, which is split using `shlex.split`.

    Args:
        cmd: the command to run.

    Returns:
        int: the return code of the call.
    """
    return _call(cmd, **kwargs)[0]


def check_call(cmd, **kwargs):
    """A convenient version of `subprocess.check_call`.

    Similar in behavior to `subprocess.check_call`, but accepts the args as a
    single string, which is split using `shlex.split`.

    Args:
        cmd: the command to run.

    Raises:
        Exception: if the call returns a non-zero return code.

    Returns:
        str: the output from `stdout`, as a utf-8 string.
    """
    returncode, stdoutdata, stderrdata = _call(cmd, **kwargs)
    if returncode:
        message = ''
        if stderrdata:
            message += '\nstderr:\n{}\n'.format(stderrdata)
        if stdoutdata:
            message += '\nstdout:\n{}\n'.format(stdoutdata)
        raise CallError(message.strip())
    return stdoutdata
