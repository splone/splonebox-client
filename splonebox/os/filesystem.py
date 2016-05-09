"""
This file is part of the splonebox python client library.

The splonebox python client library is free software: you can
redistribute it and/or modify it under the terms of the GNU Lesser
General Public License as published by the Free Software Foundation,
either version 3 of the License or any later version.

It is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with this splonebox python client library.  If not,
see <http://www.gnu.org/licenses/>.

"""

import os
import fcntl


def open_lock(filename):
    fd = os.open(filename, os.O_RDWR | os.O_CLOEXEC)

    try:
        fcntl.lockf(fd, fcntl.LOCK_EX)
    except OSError:
        os.close(fd)
        raise

    return fd


def open_write(filename):
    fd = os.open(filename, os.O_CREAT | os.O_WRONLY | os.O_NONBLOCK |
                 os.O_CLOEXEC, 0o600)

    return fd


def save_sync(filename, data: bytes):
    fd = open_write(filename)

    filed = open(fd, "wb")
    filed.write(data)
    os.close(fd)
