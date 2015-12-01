from Splonecli.Connection.message import MRequest

# TODO: This whole thing might get removed. -- Message and Apicall should be merged if possible
class Apicall:
    """
    Wraps :class:`Message` for convenience

    splonebox specific messages are defined here
    """
    def __init__(self):
        self.request = MRequest()

    @staticmethod
    def from_Request(msg: MRequest):
        """


        :param msg:
        :return:
        """
        name = msg.method
        if  name == "register":
            call = Apicall()
            call.request = msg
            call.__class__ = ApiRegister
            return call
        elif name == "run":
            call = Apicall()
            call.request = msg
            call.__class__ = ApiRun
            return call

        return None

class ApiRegister(Apicall):
    """
    Register Api call.

    [
        msgid, # some random number. Handled my :class: `Message`
        type,  # 0 Since it is a Request Type (See :class: `Message`)
        method, # "register" for obvious reasons
        [
            [                          # Metadata
                <api key>,
                <plugin name>,
                <description>,
                ...
            ],
            [                          # List of functions
                [                      # Function description (See :Plugin:)
                    <function name>,
                    <function descripton>,
                    [<arg (="")>, <arg(=0)>] # Some Value is given to identify the type
                                             # Usually "" for string, 0 for int ,
                                             # b'' for binary data , 0.0 for float, False for Bool
                ]
                []
            ]

        ]
    ]
    """
    def __init__(self, metadata, functions):
        super().__init__()
        self.request.method = "register"
        self.request.body = [metadata, functions]


class ApiRun(Apicall):
    """
    Run Api call

    [
        msgid, # some random number. Handled my :class: `Message`
        type,  # 0 Since it is a Request Type (See :class: `Message`)
        method, # "run" for obvious reasons
        [
            [                          # Metadata
                <api key>
            ],
            <function name>,
            [                          # Functions
                <arg1>,
                <arg2>,
                ...
            ]
    ]
    """
    def __init__(self, apikey: str, function_name: str, args: []):
        super().__init__()
        self.request = MRequest()
        self.request.method = "run"
        self.request.body = [[apikey], function_name, args]

    def get_method_args(self):
        return self.request.body[2]

    def get_api_key(self):
        return self.request.body[0][0].decode('ascii')

    def get_method_name(self):
        return self.request.body[1].decode('ascii')
