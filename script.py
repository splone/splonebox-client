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

