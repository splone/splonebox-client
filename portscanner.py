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
import socket
import sys
from datetime import datetime
# ---- THIS IS A TEST PLUGIN ---
from Splonecli.Api.plugin import RemoteFunction


@RemoteFunction
def portscan(ip: ctypes.c_char_p, p_range_start: ctypes.c_int64, p_range_end: ctypes.c_int64):
    """
    Please Note, 99% of this code is stolen from here:
    http://www.pythonforbeginners.com/code-snippets-source-code/port-scanner-in-python
    """
    print(p_range_start, " ", p_range_end)
    assert (p_range_end >= 0 and p_range_start >= 0)
    # Enter Host to scan
    remoteServerIP = socket.gethostbyname(ip)

    # This is just a nice touch that prints out information on which host we are about to scan
    print("-" * 60)
    print("Please wait, scanning remote host", remoteServerIP)
    print("-" * 60)

    # Check what time the scan started
    t1 = datetime.now()

    # Using the range function to specify ports (here it will scans all ports between 1 and 1024)
    # We also put in some error handling for catching errors
    returnval = []
    try:
        for port in range(p_range_start, p_range_end):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((remoteServerIP, port))
            if result == 0:
                # if a socket is listening it will print out the port number
                print("Port {}: \t Open".format(port))
                returnval.append(port)
            sock.close()


    # Dont press any buttons or you will screw up the scanning, so i added a keyboard exception
    except KeyboardInterrupt:
        print("You pressed Ctrl+C")
        sys.exit()
    # Here is my host execption, incase you typed it wrong. ( i guess maybe i should have added this up top)
    except socket.gaierror:
        print("Hostname could not be resolved. Exiting")
        sys.exit()
    # finally socket error incase python is having trouble scanning or resolving the port
    except socket.error:
        print("Couldn't connect to server")
        sys.exit()

    # Checking the time again
    t2 = datetime.now()

    # Calculates the difference of time, to see how long it took to run the script
    total = t2 - t1

    # Printing the information to screen
    print('Scanning Completed in: ', total)
    return returnval
