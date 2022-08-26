import collections
from abc import ABC, abstractmethod


class TreeFormatter(ABC):
    @abstractmethod
    def root(self) -> str:
        pass

    @abstractmethod
    def record(self, last) -> str:
        pass

    @abstractmethod
    def directory(self, last) -> str:
        pass

    @abstractmethod
    def dir_children(self, last) -> str:
        pass

class TreeFormatterPlain(TreeFormatter):
    def root(self):
        return "|"

    def record(self, last):
        return "+--"

    def directory(self, last):
        return "+->"
            
    def dir_children(self, last):
        if last:
            return "  "
        else:
            return "| "

class TreeFormatterFancy(TreeFormatter):
    def root(self):
        return "╮"

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

def match_case_insensitive(input, search_term):
    return input.lower().find(search_term.lower()) >= 0

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
            if match_case_insensitive(path, search_term):
                return True
        return False

    def filtered_records(self, search_term):
        for name, path in self.records.items():
            if match_case_insensitive(path, search_term):
                yield name

    def filtered_subdirs(self, search_term):
        for name, subdir in self.subdirs.items():
            if subdir.contains(search_term):
                yield name, subdir

    def tree_str(self, fmt: TreeFormatter, search_term: str="", prefix: str=None):
        """
        Args:
            fmt: TreeFormatter instance, allowing output customization
            search_term: Include only parts of the Tree that contain this string.
            prefix: Prepended to each line. Used for indentation during recursive calls. 
        """
        if prefix==None:
            prefix = ""
            r = fmt.root()
            if r:
                yield r

        filtered_subdirs = list(self.filtered_subdirs(search_term))
        filtered_records = list(self.filtered_records(search_term))
        
        for idx, (name, subdir) in enumerate(filtered_subdirs):
            last = (idx == len(filtered_subdirs)-1) and len(filtered_records)==0
            yield f"{prefix}{fmt.directory(last)} {name}/"
            yield from subdir.tree_str(fmt, search_term, prefix+fmt.dir_children(last))

        for idx, name in enumerate(filtered_records):
            last = (idx == len(filtered_records)-1)
            yield f"{prefix}{fmt.record(last)} {name}"

class PathTree:
    def __init__(self, db):
        self.db = db
        self._root = None
        self.reload_counter = 0

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

        self.reload_counter += 1
    
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

    def tree_str(self, search_term: str="", fmt: TreeFormatter=TreeFormatterPlain()) -> str:
        return "\n".join(self.root.tree_str(fmt, search_term))