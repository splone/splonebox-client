from Splonecli.Rpc.message import MRequest, MResponse


class Apicall:
    """
    Wraps :class:`Message` for convenience
    This is mostly here to show what the calls look like.

    splonebox specific messages are defined here
    """

    def __init__(self):
        self.msg = MRequest()

    @staticmethod
    def from_Request(msg: MRequest):
        """
        :param msg:
        :return:
        """
        name = msg.method
        if name == "run":
            call = Apicall()
            call.msg = msg
            call.msg.body[0][0] = call.msg.body[0][0].decode('ascii')
            call.msg.body[1] = call.msg.body[1].decode('ascii')
            call.__class__ = ApiRun
            return call
        raise InvalidApiCallError()


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
        self.msg.method = "register"
        self.msg.body = [metadata, functions]


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
        self.msg = MRequest()
        self.msg.method = "run"
        self.msg.body = [[apikey], function_name, args]

    def get_method_args(self):
        return self.msg.body[2]

    def get_api_key(self) -> str:
        return self.msg.body[0][0]

    def get_method_name(self) -> str:
        return self.msg.body[1]


class InvalidApiCallError(Exception):
    def __init__(self, value: str):
        self.value = value

    def __str__(self) -> str:
        return self.value
