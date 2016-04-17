# Copyright 2015-2016 D.G. MacCarthy <devwigs@gmail.com>
#
# This file is part of WIGS.
#
# WIGS is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# WIGS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with WIGS.  If not, see <http://www.gnu.org/licenses/>.


from wsgiref.simple_server import make_server, WSGIRequestHandler
from urllib.parse import unquote
from sys import stderr
from json import dumps
from time import sleep


class Handler(WSGIRequestHandler):

    def xlog_message(self, frmt, *args):
        "Disable request log"
        pass


class Server():
    kill = False
    voices = None

    def __init__(self, port=8002):
        self.port = port
        self.queue = []
        Server.instance = self

    @staticmethod
    def wsgi(env, start_response):
        s = Server.instance
        try:
            n = ("/", "/cmd", "/voice").index(env["PATH_INFO"])
        except:
            n = -1
        if n == 0:
            yield s.send(Server.html, start_response, "text/html")
        elif n < 0:
            yield s.send("Not found", start_response, "text/plain", "404 Not Found")
        else:
            if n == 2:
                q = unquote(env["QUERY_STRING"])
                if len(q):
                    s.voices = q.split("&")
                    data = {}
                else: data = s.voices
            else:
                data = s.queue
                s.queue = []
                n = len(data)
                if n: print("Sending {} utterances.".format(n), file=stderr)
            yield s.send(dumps(data), start_response, "application/json")

    @staticmethod
    def send(text, start_response, mime, status="200 OK"):
        response = text.encode("utf8")
        headers = [("Content-Type", mime), ("Content-Length", str(len(response)))]
        start_response(status, headers)
        return response

    def run(self):
        ip = "127.0.0.1"
        msg = "{{}} server on http://{}:{}.".format(ip, self.port)
        self.srv = make_server(ip, self.port, self.wsgi, handler_class=Handler)
        print(msg.format("Starting"), file=stderr)
        while True:
            self.srv.handle_request()

    def say(self, text, **kwargs):
        data = {"text":text}
        data.update(kwargs)
        self.queue.append(data)

    with open("index.html") as f: html = f.read()


class Voice:
    server = None

    @classmethod
    def init(cls, port=8002):
        cls.server = Server(port).start()
        n = 0
        while cls.server.voices is None:
            sleep(0.20)
            if n == 0: print("Waiting for client...", file=stderr)
            n = (1 + n) % 20

    @classmethod
    def stop(cls): return cls.server.stop()

    @classmethod
    def names(cls): return cls.server.voices

    @classmethod
    def findVoice(cls, data):
        v = data.get("voice")
        if type(v) is str:
            names = [name.lower() for name in v.split(" ")]
            words = []
            v = cls.server.voices
            for i in range(len(v)):
                vName = [name.lower() for name in v[i].split(" ")]
                count = 0
                for j in range(len(names)):
                    if names[j] in vName: count += 1
                words.append(count);
            j = 0
            count = words[0]
            for i in range(1, len(words)):
                if words[i] > count:
                    j = i
                    count = words[i]
            data["voice"] = j

    @classmethod
    def printNames(cls):
        v = cls.server.voices
        for i in range(len(v)):
            print("{:3d} {}".format(i, v[i]))

    def config(self, **kwargs):
        if self.server is None:
            Voice.init()
        self.voice = 0
        self.findVoice(kwargs)
        self.__dict__.update(kwargs)
    
    __init__ = config

    def say(self, *text, **kwargs):
        data = {}
        data.update(self.__dict__)
        data.update(kwargs)
        after = data.get("after")
        if after is not None: del data["after"]
        n = len(text)
        for i in range(n):
            if i == n-1 and after is not None:
                data["pause"] = after
            self.server.say(text[i], **data)
        if data.get("end"):
            self.stop()

Server().run()
#alex = Voice(voice="Google UK English Female")
