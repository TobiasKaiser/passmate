import collections


class TreeFormatter:
    def record(self, last):
        if last:
            return "╰──"
        else:
            return "├──" 

    def directory(self, last):
        if last:
            return "╰─┬"
        else:
            return "├─┬"

    def dir_children(self, last):
        if last:
            return "  "
        else:
            return "│ "

class Directory:
    def __init__(self, parent):
        self.parent = parent
        self.subdirs={}
        self.records={}

    def contains(self, search_term):
        for subdir in self.subdirs.values():
            if subdir.contains(search_term):
                return True
        for path in self.records.values():
            # We use self.records.values() instead of just self.records.keys() here
            # to allow search terms that cross directory levels (e. g. "path/record"). 
            if path.find(search_term) >= 0:
                return True
        return False

    def print(self, search_term="", fmt=TreeFormatter(), prefix=""):
        """
        Args:
            search_term: Include only parts of the Tree that contain this string.
            fmt: TreeFormatter instance
            prefix: Prepended to each line. Used for indentation during recursive calls. 
        """
        if not self.contains(search_term):
            return

        for idx, (name, subdir) in enumerate(self.subdirs.items()):
            last = (idx == len(self.subdirs)-1) and len(self.records)==0
            
            print(f"{prefix}{fmt.directory(last)} {name}/")
            
            fmt_children = fmt.dir_children(last)
            subdir.print(search_term, fmt, prefix+fmt_children)
        for idx, name in enumerate(self.records.keys()):
            last = (idx == len(self.records)-1)
            print(f"{prefix}{fmt.record(last)} {name}")

class PathTree:
    def __init__(self, db):
        self.db = db
        self._root = None

    def invalidate(self):
        self._root = None

    @property
    def root(self):
        self.reload_hierarchy_if_invalid()
        return self._root

    def reload_hierarchy_if_invalid(self):
        if self._root:
            return

        self._root = Directory(None)

        for path in iter(self.db):
            #if self.searchterm and path.find(self.searchterm)<0:
            #    continue
            dirs, leaf = self.split_path(path)
            cur_dir = self._subdirectory(dirs)
            cur_dir.records[leaf] = path
    
    def _subdirectory(self, dirs):
        dir_iter = self._root
        for d in dirs:
            if not d in dir_iter.subdirs:
                dir_iter.subdirs[d] = Directory(dir_iter)
            dir_iter = dir_iter.subdirs[d]
        return dir_iter

    @staticmethod
    def split_path(path):
        path_split = path.split("/")
        dirs, leaf = path_split[:-1], path_split[-1]
        return list(dirs), leaf

    def print(self, search_term=""):
        print("╮")
        self.root.print(search_term)