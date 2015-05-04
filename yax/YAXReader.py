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
        if callable(tag):  # A (hopefully) bool expression
            return tag
        elif isinstance(tag, str):  # The lam.expr. will compare
            return lambda s: s == tag
        elif isinstance(tag, RE):  # The l.exp. checks with fullmatch
            return lambda s: tag.fullmatch(s) is not None
        elif isinstance(tag, list):  # The l.ex. checks the containing (str!)
            taglist = list()
            for t in tag:
                taglist.append(Condition.normalize_tag(t))

            def checktag(s):
                for l in taglist:
                    if l(s):
                        return True
                return False

            return checktag

        elif tag is True:  # True only if exists.
            return lambda s: not not s
        elif tag is None:  # If none, everything will be accepted.
            return lambda s: True
        else:
            raise AttributeError("Unexpected attribute as tag/text name filter! {}".format(type(
                tag)))

    @staticmethod
    def normalize_attrib(attrib):
        if not attrib:
            return lambda d: True
        elif isinstance(attrib, dict):
            if len(attrib) == 0:
                return lambda d: True
            for k, v in attrib.items():
                attrib[k] = Condition.normalize_tag(v)

            def checkarttr(d: dict):
                # Ha van olyan feltétel, amire nincs attr, vagy amire nem stimmel, álljon le.
                for key, check in attrib.items():
                    val = d.get(key)
                    if not val or not check(val):
                        return False
                return True

            return checkarttr
        else:
            raise AttributeError("Unexpected attribute as attrib filter! {}".format(type(attrib)))

    def __init__(self, tag=None, attrib=None, text=None,
                 parent=None, children=None, keep_children=None):

        self._inverted = False  # self doesn't matches if would be match
        self.check = self._check  # set the non-inverted check function
        # condition attributes (check callables will be created):
        self._tag = Condition.normalize_tag(tag)
        self._attrib = Condition.normalize_attrib(attrib)
        self._text = Condition.normalize_tag(text)
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
        # If any part of condition is false, return with false.
        if not self._tag(element.tag):                          # Checking tagname
            return False
        if not self._attrib(element.attrib):                    # Checking attribs
            return False
        # if not self._text(element.text.strip()):                  # Checking text
        #     return False
        #  todo: Üres text vs. whitespace
        if element.text is None:
            if not self._text(None):
                return False
        else:
            if not self._text(element.text.strip()):
                return False

        # CSAK lxml.ElementTree todo: WORKAROUND
        if LXML:
            if not self._parent.check(element.getparent()):     # Checking parent
                return False

        if not self._check_children(element):                   # Checking children
            return False

        return True

    def _inverted_check(self, element) -> bool:
        return not self._check(element)

    def keep(self, element) -> bool:
        parent = element.getparent()                    # Don't keep the root element
        if not parent or not self._tag(parent.tag):     # Element's parent must be match
            return False
        for ch_cond in self._children:                  # Keep if it is in the children conditions
            if ch_cond.check(element):
                return True
        for keep_cond in self._keep:                    # Keep if it is in the keep conditions
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
    def _default(*args):
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
        # This is the main part of the element processing.
        def process_element(e):
            keep = False                            # Do not keep anything by default.
            for cond, cb_runner in self._cnds:      # For all conditions.
                if cond.check(e):                   # When matches, run the callback.
                    cb_runner(e)
                if keep:                            # If already keep, go to next.
                    continue
                if cond.keep(e):                    # If has to be kept, set keep.
                    keep = True
            if not keep:                            # After all condition delete if not keep.
                del e.getparent()[e.getparent().index(e)]

        if not self._stream:
            raise AttributeError("Input stream is not initialized.")
        elif self._stream.closed:
            raise AttributeError("The input stream is closed.")
        parser = etree.XMLPullParser(events=('end',))
        # Reading the stream until end.
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
