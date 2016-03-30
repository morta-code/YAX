import re
import inspect
from .condition import Condition
import warnings

__author__ = 'Móréh, Tamás'


# Type of compiled regexes
RE = type(re.compile(""))


def element_to_string(element, encoding="unicode", method="xml", **kwargs):
    return YAXReader.etree.tostring(element, encoding=encoding, method=method, **kwargs)


def element_to_cmplx_dict(element):
    # {tag: "", attrib: {}, text: "", children: {}, childlist: []}
    d = dict()
    d["tag"] = element.tag
    d["attrib"] = element.attrib
    d["text"] = element.text
    chd = {}
    chl = []
    for child in list(element):
        cd = element_to_cmplx_dict(child)
        chl.append(cd)
        chd[cd["tag"]] = cd
    d["children"] = chd
    d["childlist"] = chl
    return d


def element_to_json_dict(element, attrib_prefix="-", text_prefix="#"):
    tag = element.tag
    text = [element.text.strip() if element.text is not None else "", ]
    d = dict()

    for a, v in element.attrib.items():
        if d.get(attrib_prefix + a):
            c = d[attrib_prefix + a]
            if isinstance(c, list):
                c.append(v)
            else:
                d[attrib_prefix + a] = [c, v]
        else:
            d[attrib_prefix + a] = v

    for child in list(element):
        text.append(child.tail.strip() if child.tail is not None else "")
        ch = element_to_json_dict(child)
        if d.get(child.tag):
            c = d[child.tag]
            if isinstance(c, list):
                c.append(ch[child.tag])
            else:
                d[child.tag] = [c, ch[child.tag]]
        else:
            d[child.tag] = ch[child.tag]

    # clean text
    t2 = []
    for t in text:
        if t:
            t2.append(t)
    text = t2
    if len(text) == 1:
        text = text[0]
    # add text if exists
    if len(d) == 0:
        d = text
    elif text:
        d[text_prefix + "text"] = text
    return {tag: d}


class CallbackRunner:
    ETREE = 1
    STRING = 2
    DICT = 3
    JSON_DICT = 4
    ATTRIB_PREFIX = "-"
    TEXT_PREFIX = "#"

    @staticmethod
    def _default(*args):
        pass

    @staticmethod
    def _convert_to_string(e):
        return YAXReader.etree.tostring(e)

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
        tag = e.tag
        text = [e.text.strip() if e.text is not None else "", ]
        d = dict()

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
            text.append(child.tail.strip() if child.tail is not None else "")
            ch = CallbackRunner._convert_to_json_dict(child)
            if d.get(child.tag):
                c = d[child.tag]
                if isinstance(c, list):
                    c.append(ch[child.tag])
                else:
                    d[child.tag] = [c, ch[child.tag]]
            else:
                d[child.tag] = ch[child.tag]

        # clean text
        t2 = []
        for t in text:
            if t:
                t2.append(t)
        text = t2
        if len(text) == 1:
            text = text[0]
        # add text if exists
        if len(d) == 0:
            d = text
        elif text:
            d[CallbackRunner.TEXT_PREFIX+"text"] = text
        return {tag: d}

    @staticmethod
    def _convert_to_element(e):
        return e

    def __init__(self, t: int, attrib_prefix='-', text_prefix='#', condition: Condition=None):
        self.condition = condition
        self._callback = CallbackRunner._default
        self._type = t
        CallbackRunner.ATTRIB_PREFIX = attrib_prefix
        CallbackRunner.TEXT_PREFIX = text_prefix
        if t == CallbackRunner.ETREE:
            self._convert = CallbackRunner._convert_to_element
        elif t == CallbackRunner.STRING:
            self._convert = CallbackRunner._convert_to_string
        elif t == CallbackRunner.DICT:
            self._convert = CallbackRunner._convert_to_cmplx_dict
        elif t == CallbackRunner.JSON_DICT:
            self._convert = CallbackRunner._convert_to_json_dict
        else:
            raise Exception("CallbackRunner type must be one of CallbackRunner.ETREE, " +
                            "CallbackRunner.STRING, CallbackRunner.JSON_DICT and " +
                            "CallbackRunner.DICT!")

    def inverted(self) -> Condition:
        warnings.warn("This feature is waiting for a better implementation", FutureWarning)
        self.condition.inverse()
        return self

    # TODO itt kell megvalósítani a visszaírást

    def calls(self, callback):
        if not callable(callback):
            raise Exception("The callback argument must be callable!")
        ins = inspect.getfullargspec(callback)
        if len(ins.args) < 2 and ins.varargs is None:
            raise Exception("The callback funciton must can accept at least 2 arguments!\n" +
                            "First: The element itself, Second: the line number.")
        self._callback = callback

    def __call__(self, element, line: int=0):
        self._callback(self._convert(element), line)


class YAXReader:
    etree = None  # todo példány szintre! (egyébként működik)

    def __init__(self, stream=None, use_lxml=False):
        self._cnds = []
        self.stream = stream
        if use_lxml:
            try:
                import lxml.etree as etree
                Condition.LXML = True
            except ImportError:
                import xml.etree.ElementTree as etree
                Condition.LXML = False
        else:
            import xml.etree.ElementTree as etree
            Condition.LXML = False
        YAXReader.etree = etree

    @staticmethod
    def lxml_in_use():
        return Condition.LXML

    def start(self, chunk_size=8192):
        if not self.stream:
            raise Exception("Input stream is not initialized.")
        elif self.stream.closed:
            raise Exception("The input stream is closed.")
        if Condition.LXML:
            parser = YAXReader.etree.XMLPullParser(events=('end',))
            prev_parent = None
            prev_element = None
            keep = False
            chunk = self.stream.read(chunk_size)
            while chunk:
                parser.feed(chunk)
                for action, element in parser.read_events():
                    if not keep and prev_parent is not None:
                        prev_parent.remove(prev_element)
                    keep = False
                    for cond, cb_runner in self._cnds:
                        if cond.check(element):
                            cb_runner(element)
                        if not keep and cond.keep(element):
                            keep = True
                    prev_parent = element.getparent()
                    prev_element = element
                chunk = self.stream.read(chunk_size)
        else:
            parser = YAXReader.etree.XMLPullParser(events=('end', 'start'))
            parents = []
            chunk = self.stream.read(chunk_size)
            while chunk:
                parser.feed(chunk)
                for action, element in parser.read_events():
                    if action == 'start':
                        parents.append(element)
                    else:
                        parents.pop()
                        keep = False                            # Do not keep anything by default.
                        for cond, cb_runner in self._cnds:      # For all conditions.
                            if cond.check(element, parents):
                                cb_runner(element)
                            if not keep and cond.keep(element, parents):
                                keep = True
                        if not keep and len(parents) > 0:
                            parents[-1].remove(element)
                chunk = self.stream.read(chunk_size)
        self.stream.close()

    def find(self, tag=None, attrib: dict=None, text=None,
             parent=None, children=None, keep_children=None) -> CallbackRunner:
        tup = (Condition(tag, attrib, text, parent, children, keep_children),
               CallbackRunner(CallbackRunner.ETREE))
        self._cnds.append(tup)
        tup[1].condition = tup[0]
        return tup[1]

    def match(self, cond: Condition) -> CallbackRunner:
        tup = (cond, CallbackRunner(CallbackRunner.ETREE))
        self._cnds.append(tup)
        tup[1].condition = tup[0]
        return tup[1]

    # TODO remove deprecated funcs
    def find_as_element(self, tag=None, attrib: dict=None, text=None,
                        parent=None, children=None, keep_children=None) -> CallbackRunner:
        warnings.warn("Deprecated: this method will be removed in version 2.0.\n"
                      "Use the new converter methods.", DeprecationWarning)
        tup = (Condition(tag, attrib, text, parent, children, keep_children),
               CallbackRunner(CallbackRunner.ETREE))
        self._cnds.append(tup)
        tup[1].condition = tup[0]
        return tup[1]

    def find_as_str(self, tag=None, attrib: dict=None, text=None,
                    parent=None, children=None, keep_children=None) -> CallbackRunner:
        warnings.warn("Deprecated: this method will be removed in version 2.0.\n"
                      "Use the new converter methods.", DeprecationWarning)
        tup = (Condition(tag, attrib, text, parent, children, keep_children),
               CallbackRunner(CallbackRunner.STRING))
        self._cnds.append(tup)
        tup[1].condition = tup[0]
        return tup[1]

    def find_as_dict(self, tag=None, attrib: dict=None, text=None,
                     parent=None, children=None, keep_children=None) -> CallbackRunner:
        warnings.warn("Deprecated: this method will be removed in version 2.0.\n"
                      "Use the new converter methods.", DeprecationWarning)
        tup = (Condition(tag, attrib, text, parent, children, keep_children),
               CallbackRunner(CallbackRunner.DICT))
        self._cnds.append(tup)
        tup[1].condition = tup[0]
        return tup[1]

    def find_as_json_dict(self, tag=None, attrib: dict=None, text=None,
                          parent=None, children=None, keep_children=None) -> CallbackRunner:
        warnings.warn("Deprecated: this method will be removed in version 2.0.\n"
                      "Use the new converter methods.", DeprecationWarning)
        tup = (Condition(tag, attrib, text, parent, children, keep_children),
               CallbackRunner(CallbackRunner.JSON_DICT))
        self._cnds.append(tup)
        tup[1].condition = tup[0]
        return tup[1]

    def match_as_element(self, cond: Condition) -> CallbackRunner:
        warnings.warn("Deprecated: this method will be removed in version 2.0.\n"
                      "Use the new converter methods.", DeprecationWarning)
        tup = (cond, CallbackRunner(CallbackRunner.ETREE))
        self._cnds.append(tup)
        tup[1].condition = tup[0]
        return tup[1]

    def match_as_str(self, cond: Condition) -> CallbackRunner:
        warnings.warn("Deprecated: this method will be removed in version 2.0.\n"
                      "Use the new converter methods.", DeprecationWarning)
        tup = (cond, CallbackRunner(CallbackRunner.STRING))
        self._cnds.append(tup)
        tup[1].condition = tup[0]
        return tup[1]

    def match_as_dict(self, cond: Condition) -> CallbackRunner:
        warnings.warn("Deprecated: this method will be removed in version 2.0.\n"
                      "Use the new converter methods.", DeprecationWarning)
        tup = (cond, CallbackRunner(CallbackRunner.DICT))
        self._cnds.append(tup)
        tup[1].condition = tup[0]
        return tup[1]

    def match_as_json_dict(self, cond: Condition) -> CallbackRunner:
        warnings.warn("Deprecated: this method will be removed in version 2.0.\n"
                      "Use the new converter methods.", DeprecationWarning)
        tup = (cond, CallbackRunner(CallbackRunner.JSON_DICT))
        self._cnds.append(tup)
        tup[1].condition = tup[0]
        return tup[1]
