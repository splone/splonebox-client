import portscanner

from Splonecli.Api.plugin import Plugin


# ------ MY PERSONAL PLAYGROUND (might be interesting though )-----

plug = Plugin("yv7620iBlGgl8WzlpuU5PQjrIRwSEZOUwV2ukxWAxt3vOUl41MQwT8JSqGB4JRI",
                 "bens super plugin", "Simply incredible", "MIT", "Guy")

plug.connect('127.0.0.1', 6666)
plug.register()

# test the port scanner
plug.run(plug.metadata[0], "portscan", ["127.0.0.1", 0, 1000])

plug.wait()

print()