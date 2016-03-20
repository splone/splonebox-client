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

import socket
from queue import Queue
from unittest.mock import Mock
from splonecli.api.plugin import Plugin
from splonecli.rpc import connection
from splonecli.rpc.connection import Connection
from splonecli.rpc.msgpackrpc import MsgpackRpc


# noinspection PyProtectedMember
def plug_rpc_connect(plug: Plugin) -> Mock:
    # Check for reference: https://docs.python.org/3/library/unittest.mock.html
    plug._rpc.connect = Mock()
    return plug._rpc.connect


# noinspection PyProtectedMember
def plug_rpc_send(plug: Plugin) -> Mock:
    plug._rpc.send = Mock()
    return plug._rpc.send


# noinspection PyProtectedMember
def connection_socket(con: Connection) -> Mock:
    con._socket = Mock(spec=socket.socket)
    return con._socket


# noinspection PyProtectedMember
def connection_socket_fake_recv(con: Connection) -> Queue:
    con._socket = Mock(spec=socket.socket)
    q = Queue(maxsize=1)
    con._socket.recv = q.get
    return q


# noinspection PyProtectedMember
def connection_listen_thread(con: Connection) -> Mock:
    con.start_new_thread = Mock()
    return con.start_new_thread


# noinspection PyProtectedMember
def rpc_connection_send(mprpc: MsgpackRpc) -> Mock:
    mprpc._connection.send_message = Mock()
    return mprpc._connection.send_message


# noinspection PyProtectedMember
def rpc_dispatch(mprpc: MsgpackRpc, name: str) -> Mock:
    mprpc._dispatcher[name] = Mock()
    return mprpc._dispatcher[name]


# noinspection PyProtectedMember
def rpc_handle_response(mprpc: MsgpackRpc) -> Mock:
    mprpc._handle_response = Mock()
    return mprpc._handle_response


# noinspection PyProtectedMember
def rpc_handle_notify(mprpc: MsgpackRpc) -> Mock:
    mprpc._handle_notify = Mock()
    return mprpc._handle_notify


def rpc_send(mprpc: MsgpackRpc) -> Mock:
    mprpc.send = Mock()
    return mprpc.send


def receive(plug: Plugin):
    pass
