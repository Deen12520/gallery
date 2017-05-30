import tornado.ioloop
import tornado.httpserver
import tornado.web
import os
import sys

# Set up current directory to program directory
os.chdir(os.path.join(os.getcwd(), os.path.dirname(sys.argv[0])))

from handler.gallery import *

application = tornado.web.Application([
    (r"/", tornado.web.RedirectHandler, {"url": "/gallery/"}),
    (r"/gallery/(.*)", GalleryHandler),
    (r"/preview/(small|large|medium)/(.+)", PreviewHandler),
    (r"/download/(.+)", DownloadHandler),
    (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": "static"}),
], template_path = "template", static_path = "static")

if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
