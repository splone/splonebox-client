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

import ctypes

from Splonecli.Api.remotefunction import RemoteFunction
from Splonecli.Api.plugin import Plugin


@RemoteFunction
def foo(x: ctypes.c_char_p):
	print(x)

apikey = "<put valid api key here>" # !!!

plug = Plugin(apikey, "abc", "abc", "abc", "abc", debug=True)

plug.connect("127.0.0.1", 6666) # Whatever port & ip are

### Non-Blocking Register Call

res = plug.register(blocking=False) # make call non blocking


# !!!! Result response is not implemented @ server yet.
# DO NOT WAIT FOR A RESPONSE!

# res is :RegisterResult (see result.py)
# try:
#	 res.await() # block untill register finishes, raises remote error
# except RemoteError:
#	 pass # somethign went wrong

### Blocking register Call
# plug.register()


result = plug.run(apikey, "foo", ["Hello World!"])

plug.listen() # just wait for incomming messages

# plug.stop() # make sure to stop the plugin IF you don't listen

