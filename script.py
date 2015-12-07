import time

import portscanner # Import is needed to make sure annotations get checked

from Splonecli.Api.plugin import Plugin, RemoteFunction

# ------ MY PERSONAL PLAYGROUND (might be interesting though )-----

plug = Plugin("IZgSrbBrEScouCpAzAnv8yi0oLMXCskWmuXhAmSPc4Nxtc54xuNDiS8HSUUZd7K",
                 "bens super plugin", "Simply incredible", "MIT", "Guy")

plug.connect('127.0.0.1', 6666)
plug.register()

# test the port scanner
plug.run(plug.metadata[0], "portscan", ["127.0.0.1", 0, 100])

time.sleep(2)
plug.run(plug.metadata[0], "stop",[])


plug.wait()


