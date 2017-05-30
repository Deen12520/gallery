import tornado.web 
import os
from PIL import Image
import hashlib
import datetime
import email
import time

home_dir = "E:/your photo path"    # replace with your path of photo
cache_dir = "cache"

class GalleryHandler(tornado.web.RequestHandler):
    def build_paths(self, path):
        """Turn /root/home/www into 
            1. root
            2. root/home
            3. root/home/www
        """
        paths = []
        path_segments = path.strip('/').split('/')
        for x in range(len(path_segments)):
            if path_segments[x] != '':
                paths.append((path_segments[x], "/".join(path_segments[:x+1])))
        return paths
    
    def is_picture(self, fpath):
        return os.path.splitext(fpath)[1].lower() in ('.jpg', '.png')
        
    def get(self, path):
        #print "get", path, 'from', self.request.remote_ip
        print("get {0} from {1}".format(path,self.request.remote_ip))
        path = path.strip('/')
        paths = self.build_paths(path)
        target_dir = os.path.join(home_dir, path)
        fname = os.path.basename(path)
        if os.path.isdir(target_dir):
            files = self.search_files(target_dir, path)
            self.render("gallery.html", paths=paths, path=path, files=files, fname=fname)
        else:
            image_url = self.add_tag('/preview/large/' + path, target_dir)
            target_dir = os.path.dirname(target_dir)
            files = self.search_neighbor_files(target_dir, path, fname)
            # Add ?v=***
            files_tags = [self.add_tag(x, os.path.join(target_dir, os.path.basename(x))) for x in files]
            self.render("slide.html", paths=paths, files_tags=files_tags, files=files, 
                path=path, image_url=image_url, fname=fname)
    
    def search_neighbor_files(self, target_dir, path, fname):
        total_count = 9
        files = [path]
        flist = [x for x in os.listdir(target_dir) if self.is_picture(x)]
        flist.sort()
        index = flist.index(fname)
        left_it, right_it = index-1, index+1
        parent_dir = os.path.dirname(path)
        while len(files) < total_count and (left_it >= 0 or right_it < len(flist)):
            if right_it < len(flist):
                files.append(os.path.join(parent_dir, flist[right_it]))
                right_it += 1
            if len(files) < total_count and left_it >= 0:
                files.insert(0, os.path.join(parent_dir, flist[left_it]))
                left_it -= 1
        return files
    
    def add_tag(self, url, fpath):
        return url + '?v=' + str(int(os.path.getmtime(fpath)))
    
    def search_files(self, target_dir, path):
        files = []
        flist = os.listdir(target_dir)
        flist.sort()
        for fname in flist:
            fpath = os.path.join(target_dir, fname)
            if os.path.isdir(fpath):
                files.append({'is_dir': True, 'name': fname, 
                    'image_url': self.static_url('image/folder.png')})
        for fname in flist:
            fpath = os.path.join(target_dir, fname)
            if os.path.isfile(fpath) and self.is_picture(fpath):
                image_url = self.add_tag(os.path.join('/preview/small', path, fname), fpath)
                files.append({'is_dir': False, 'name': fname, 
                    'image_url': image_url})
        return files

class PreviewHandler(tornado.web.RequestHandler):
    size_types = {'small': 
                    {'squared':True, 
                     'size':(128,128)}, 
                 'medium':
                    {'squared':False,
                     'size': (600,600)},
                 'large':
                    {'squared':False,
                     'size': (800, 800)}
                }
    def build_thumbnail(self, stype, path):
        path = path.strip('/')
        tb_hash = hashlib.md5(path.encode('utf-8')).hexdigest() + '_' + stype
        tb_path = os.path.join(cache_dir, tb_hash)
        if not os.path.exists(tb_path):
            size_type = self.size_types[stype]
            fpath = os.path.join(home_dir, path)
            tb_maker = ThumbnailMaker(fpath)
            tb_maker.create(size_type['size'], tb_path, size_type['squared'])
        return tb_path
        
    def get(self, stype, path):
        tb_path = self.build_thumbnail(stype, path)
        modified = datetime.datetime.fromtimestamp(os.path.getmtime(tb_path))
        self.set_header("Last-Modified", modified)
        if "v" in self.request.arguments:
            self.set_header("Expires", datetime.datetime.utcnow() + \
                                       datetime.timedelta(days=365*10))
            self.set_header("Cache-Control", "max-age=" + str(86400*365*10))
        else:
            self.set_header("Cache-Control", "public")
        self.set_header('Content-Type', 'image/jpeg')
            
        # Check the If-Modified-Since, and don't send the result if the
        # content has not been modified
        ims_value = self.request.headers.get("If-Modified-Since")
        if ims_value is not None:
            date_tuple = email.utils.parsedate(ims_value)
            if_since = datetime.datetime.fromtimestamp(time.mktime(date_tuple))
            if if_since >= modified:
                self.set_status(304)
                return
                
        data = open(tb_path, 'rb').read()
        self.set_header('Content-Length', len(data))
        self.write(data)

class DownloadHandler(tornado.web.RequestHandler):
    def get(self, path):
        fpath = os.path.join(home_dir, path.strip('/'))
        data = open(fpath, 'rb').read()
        self.set_header('Content-Type', 'image/jpeg')
        self.set_header('Content-Length', len(data))
        self.write(data)

class ThumbnailMaker:
    def __init__(self, fpath):
        self.fpath = fpath
        
    def square(self):
        width, height = self.image.size
        if width > height:
            delta = (width - height)/2
            upper, lower = 0, height
            left = delta
            right = width - delta
        else:
            delta = (height - width)/2
            left, right = 0, width
            upper = delta
            lower = height - delta
        self.image = self.image.crop((left, upper, right, lower))
        
    def rotate(self):
        try:
            orientation = self.image._getexif()[274]       
            if orientation == 3:
                self.image = self.image.rotate(180)
            elif orientation == 6:
                self.image = self.image.rotate(-90)
            elif orientation == 8:
                self.image = self.image.rotate(90)
        except:
            pass

    def create(self, size, path, squared=True):
        self.image = Image.open(self.fpath)
        self.rotate()
        if squared:
            self.square()
        self.image.thumbnail(size, Image.ANTIALIAS)
        self.image.save(path, "JPEG", quality=90)
        del self.image