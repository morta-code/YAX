__author__ = 'Móréh, Tamás'

import io
import re

RE = type(re.compile(""))
try:
    import lxml.etree as etree

    LXML = True
except ImportError:
    import xml.etree.ElementTree as etree

    LXML = False


def debug(*s):
    print(*s)


class Condition():
    """
    Condition class for filtering the XML parse events.
    If the condition satisfies the callback function will be called.
    """

    class EmptyCondition():
        def __init__(self, b: bool):
            self._return_default = b

        def check(self, *p):
            return self._return_default


    @staticmethod
    def normalize_condition(cnd, allow_parents=True, allow_children=True, none_answer=True,
                            allow_none=True):
        def check_child(c):
            if isinstance(c, Condition) and not allow_children:
                if len(c._children) != 0:
                    raise AttributeError("Checking children of parents not allowed!")

        def check_parent(c):
            if isinstance(c, Condition) and not allow_parents:
                if not isinstance(c._parent, Condition.EmptyCondition):
                    raise AttributeError("Checking parents of child not allowed!")

        if isinstance(cnd, (str, RE)):
            return Condition(cnd)
        elif isinstance(cnd, bool):
            return Condition.EmptyCondition(cnd)
        elif cnd is None and allow_none:
            return Condition.EmptyCondition(none_answer)
        elif isinstance(cnd, (Condition, Condition.EmptyCondition)):
            check_child(cnd)
            check_parent(cnd)
            return cnd
        elif isinstance(cnd, dict):
            c = Condition(cnd.get('tag'), cnd.get('attrib'), cnd.get('text'),
                          cnd.get('parent'), cnd.get('children'), cnd.get("keep_children"))
            check_child(c)
            check_parent(c)
            return c
        elif isinstance(cnd, tuple):
            if len(cnd) == 0:
                return Condition.EmptyCondition(none_answer)
            c = Condition(*cnd)
            check_child(c)
            check_parent(c)
            return c
        else:
            raise AttributeError("Unexpected attribute as condition! {}".format(type(cnd)))

    @staticmethod
    def normalize_children(cnd) -> list:
        if cnd is None:
            return []
        if isinstance(cnd, list):
            newcnd = list()
            for c in cnd:
                # itt nem lehet EmptyCondition
                newcnd.append(
                    Condition.normalize_condition(c, allow_parents=False, allow_none=False))
            return newcnd
        else:
            # itt nem lehet EmptyCondition
            return [Condition.normalize_condition(cnd, allow_parents=False, allow_none=False), ]

    @staticmethod
    def normalize_tag(tag):
        """
        Condition tag field to lambda expression
        :param tag:
        :return: a bool lambda value
        """
        if callable(tag):  # A (hopefully) bool expression
            return tag
        elif isinstance(tag, str):  # The lam.expr. will compare
            return lambda s: s == tag
        elif isinstance(tag, RE):  # The l.exp. checks with fullmatch
            return lambda s: tag.fullmatch(s) is not None
        elif isinstance(tag, list):  # The l.ex. checks the containing (str!)
            return lambda s: s in tag
        elif tag is True:  # Ha csak létezést vizsgálunk, akkor igaz. todo:
            return lambda s: True
        elif not tag:  # If none, every tagname will be accepted.
            return lambda s: True
        else:
            raise AttributeError("Unexpected attribute as tag name filter! {}".format(type(tag)))

    @staticmethod
    def normalize_attrib(attrib):
        if not attrib:
            return lambda d: True
        elif isinstance(attrib, dict):
            for k, v in attrib.items():
                attrib[k] = Condition.normalize_tag(v)

            def checkarttr(d: dict):
                # Ha van olyan feltétel, amire nincs attr, vagy amire nem stimmel, álljon le.
                for curr_k, curr_v in d.items():
                    check = attrib.get(curr_k)
                    if not check or not check(curr_v):
                        return False
                return True

            return checkarttr
        else:
            raise AttributeError("Unexpected attribute as attrib filter! {}".format(type(attrib)))

    @staticmethod
    def normalize_text(text):
        if callable(text):
            return text
        elif isinstance(text, str):
            return lambda s: s == text
        elif isinstance(text, RE):
            return lambda s: text.fullmatch(s) is not None
        elif isinstance(text, (tuple, list)):
            return lambda s: s in text
        elif not text:
            return lambda s: True
        else:
            raise AttributeError("Unexpected attribute as text filter! {}".format(type(text)))

    def __init__(self, tag=None, attrib=None, text=None,
                 parent=None, children=None, keep_children=None):

        self._inverted = False  # self doesn't matches if would be match
        self.check = self._check  # set the non-inverted check function
        # condition attributes (check callables will be created):
        self._tag = Condition.normalize_tag(tag)
        self._attrib = Condition.normalize_attrib(attrib)
        self._text = Condition.normalize_text(text)
        self._parent = Condition.normalize_condition(parent, allow_children=False)
        self._children = Condition.normalize_children(children)
        self._keep = Condition.normalize_children(keep_children)

    def inverse_(self):
        """
        Negate the current condition
        :return: The negated condition itself.
        """
        self._inverted = not self._inverted
        if self._inverted:
            self.check = self._inverted_check
        else:
            self.check = self._check
        return self

    def _check_children(self, element):
        children = list(element)  # Every child-condition must be matching to a
        for ch_cond in self._children:  # child
            found = False
            for child in children:
                if ch_cond.check(child):
                    found = True
                    break
            if not found:
                return False
        return True

    def _check(self, element) -> bool:
        if not self._tag(element.tag):  # If tagname doesn't match, element cannot match
            return False
        if not self._attrib(element.attrib):  # If attrib doesn't match, element doesn't match
            return False
        if not self._text(element.text):  # If text doesn't match, element doesn't match
            return False

        # CSAK lxml.ElementTree todo: WORKAROUND
        if LXML:
            if not self._parent.check(element.getparent()):  # The parents checked recursivelly.
                return False

        if not self._check_children(element):
            return False

        return True

    def _inverted_check(self, element) -> bool:
        return not self._check(element)

    def keep(self, element) -> bool:
        parent = element.getparent()
        if not parent or not self._tag(parent.tag):
            return False
        for ch_cond in self._children:
            if ch_cond.check(element):
                return True
        for keep_cond in self._keep:
            if keep_cond.check(element):
                return True
        return False


class CallbackRunner():
    ETREE = 1
    STRING = 2
    DICT = 3
    JSON_DICT = 4
    ATTRIB_PREFIX = "-"

    @staticmethod
    def _default():
        pass

    @staticmethod
    def _convert_to_string(e):
        return etree.tostring(e)

    @staticmethod
    def _convert_to_cmplx_dict(e):
        # {tag: "", attrib: {}, text: "", children: {}, childlist: []}
        d = dict()
        d["tag"] = e.tag
        d["attrib"] = e.attrib
        d["text"] = e.text
        chd = {}
        chl = []
        for child in list(e):
            cd = CallbackRunner._convert_to_cmplx_dict(child)
            chl.append(cd)
            chd[cd["tag"]] = cd
        d["children"] = chd
        d["childlist"] = chl
        return d

    @staticmethod
    def _convert_to_json_dict(e):
        # Catalog: {-name: "first", PLANT: [{name: "Rózsa", }, {name: "Liliom",}]}
        # todo: ez nagyon szar, vagy? NINCS TESZTELVE
        d = {}
        for a, v in e.attrib.items():
            if d.get(CallbackRunner.ATTRIB_PREFIX + a):
                c = d[CallbackRunner.ATTRIB_PREFIX + a]
                if isinstance(c, list):
                    c.append(v)
                else:
                    d[CallbackRunner.ATTRIB_PREFIX + a] = [c, v]
            else:
                d[CallbackRunner.ATTRIB_PREFIX + a] = v
        for child in list(e):
            ch = CallbackRunner._convert_to_json_dict(child)
            if d.get(child.tag):
                c = d[child.tag]
                if isinstance(c, list):
                    c.append(ch)
                else:
                    d[child.tag] = [c, ch]
            else:
                d[child.tag] = ch
        return d


    @staticmethod
    def _convert_to_element(e):
        return e

    def __init__(self, t: int, attrib_prefix='-'):
        self._callback = CallbackRunner._default
        self._type = t
        CallbackRunner.ATTRIB_PREFIX = attrib_prefix
        if t == CallbackRunner.ETREE:
            self._convert = CallbackRunner._convert_to_element
        elif t == CallbackRunner.STRING:
            self._convert = CallbackRunner._convert_to_string
        elif t == CallbackRunner.DICT:
            self._convert = CallbackRunner._convert_to_cmplx_dict
        elif t == CallbackRunner.JSON_DICT:
            self._convert = CallbackRunner._convert_to_json_dict
        else:
            raise AttributeError("CallbackRunner type must be one of CallbackRunner.ETREE, " +
                                 "CallbackRunner.STRING, CallbackRunner.JSON_DICT and " +
                                 "CallbackRunner.DICT!")

    def calls(self, callback):
        self._callback = callback

    def __call__(self, element, line: int=0):
        self._callback(self._convert(element), line)


class YAXReader():
    def __init__(self, stream: io.TextIOBase=None):
        self._cnds = []
        self._stream = stream

    @property
    def stream(self) -> io.TextIOBase:
        return self._stream

    @stream.setter
    def stream(self, stream: io.TextIOBase):
        self._stream = stream

    @stream.deleter
    def stream(self):
        if self._stream:
            self._stream.close()
        del self._stream

    def __del__(self):
        del self.stream

    def start(self, chunk_size=10000):
        if not self._stream:
            raise AttributeError("Input stream is not initialized.")
        elif self._stream.closed:
            raise AttributeError("The input stream is closed.")

        def process_element(e):
            keep = False
            for cond, cb_runner in self._cnds:
                if cond.check(e):
                    cb_runner(e)
                if keep:
                    continue
                if cond.keep(e):
                    keep = True
            if not keep:
                del e.getparent()[e.getparent().index(e)]

        parser = etree.XMLPullParser(events=('end',))
        chunk = self._stream.read(chunk_size)
        while not chunk == "":
            parser.feed(chunk)
            for action, element in parser.read_events():
                process_element(element)
            chunk = self._stream.read(chunk_size)

    def find_as_element(self, tag=None, attrib={}, text=None,
                        parent=None, children=None, keep_children=None) -> CallbackRunner:
        tup = (Condition(tag, attrib, text, parent, children, keep_children),
               CallbackRunner(CallbackRunner.ETREE))
        self._cnds.append(tup)
        return tup[1]

    def find_as_str(self, tag=None, attrib={}, text=None,
                    parent=None, children=None, keep_children=None) -> CallbackRunner:
        tup = (Condition(tag, attrib, text, parent, children, keep_children),
               CallbackRunner(CallbackRunner.STRING))
        self._cnds.append(tup)
        return tup[1]

    def find_as_dict(self, tag=None, attrib={}, text=None,
                     parent=None, children=None, keep_children=None) -> CallbackRunner:
        tup = (Condition(tag, attrib, text, parent, children, keep_children),
               CallbackRunner(CallbackRunner.DICT))
        self._cnds.append(tup)
        return tup[1]

    def find_as_json_dict(self, tag=None, attrib={}, text=None,
                          parent=None, children=None, keep_children=None) -> CallbackRunner:
        tup = (Condition(tag, attrib, text, parent, children, keep_children),
               CallbackRunner(CallbackRunner.JSON_DICT))
        self._cnds.append(tup)
        return tup[1]

    def match_as_element(self, cond: Condition) -> CallbackRunner:
        tup = (cond, CallbackRunner(CallbackRunner.ETREE))
        self._cnds.append(tup)
        return tup[1]

    def match_as_str(self, cond: Condition) -> CallbackRunner:
        tup = (cond, CallbackRunner(CallbackRunner.STRING))
        self._cnds.append(tup)
        return tup[1]

    def match_as_dict(self, cond: Condition) -> CallbackRunner:
        tup = (cond, CallbackRunner(CallbackRunner.DICT))
        self._cnds.append(tup)
        return tup[1]

    def match_as_json_dict(self, cond: Condition) -> CallbackRunner:
        tup = (cond, CallbackRunner(CallbackRunner.JSON_DICT))
        self._cnds.append(tup)
        return tup[1]
