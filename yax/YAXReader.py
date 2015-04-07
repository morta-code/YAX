import io
import re

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

        def check(self):
            # todo: cizellálni kell egy kicsit
            return self._return_default


    @staticmethod
    def normalize_condition(cnd, allow_parents=True, allow_children=True):
        def check_child(c):
            if isinstance(c, Condition) and not allow_children:
                if not isinstance(c._children, Condition.EmptyCondition):
                    raise AttributeError("Checking children of parents not allowed!")

        def check_parent(c):
            if isinstance(c, Condition) and not allow_parents:
                if not isinstance(c._parent, Condition.EmptyCondition):
                    raise AttributeError("Checking parents of child not allowed!")

        if isinstance(cnd, bool):
            return Condition.EmptyCondition(cnd)
        elif cnd is None:
            return Condition.EmptyCondition(True)
        elif isinstance(cnd, (Condition, Condition.EmptyCondition)):
            check_child(cnd)
            check_parent(cnd)
            return cnd
        elif isinstance(cnd, dict):
            c = Condition(cnd.get('name'), cnd.get('attrs'), cnd.get('children'), cnd.get('parent'), cnd.get('text'))
            check_child(c)
            check_parent(c)
            return c
        elif isinstance(cnd, (tuple, list)):
            c = Condition(cnd[0], cnd[1], cnd[2], cnd[3], cnd[4])
            check_child(c)
            check_parent(c)
            return c
        else:
            raise AttributeError("Unexpected attribute as condition! {}".format(type(cnd)))

    @staticmethod
    def normalize_name(name):
        if callable(name):
            return name
        elif isinstance(name, str):
            return lambda s: s is name
        elif isinstance(name, type(re.compile(""))):
            return lambda s: name.fullmatch(s) is not None
        elif isinstance(name, (tuple, list)):
            return lambda s: s in name
        elif not name:
            return lambda s: True
        else:
            raise AttributeError("Unexpected attribute as tag name filter! {}".format(type(name)))

    @staticmethod
    def normalize_attrs(attrs):
        if not attrs:
            return lambda d: True
        elif isinstance(attrs, dict):
            for k, v in attrs.items():
                attrs[k] = Condition.normalize_name(v)

            def checkarttr(d: dict):    # todo: azért ezt nem árt kipróbálni
                for k, v in d.items():
                    current = attrs.get(k)
                    if current and not current(v):
                        return False
                return True

            return checkarttr

    @staticmethod
    def normalize_text(text):
        if callable(text):
            return text
        elif isinstance(text, str):
            return lambda s: s is text
        elif isinstance(text, type(re.compile(""))):
            return lambda s: text.fullmatch(s) is not None
        elif isinstance(text, (tuple, list)):
            return lambda s: s in text
        elif not text:
            return lambda s: True
        else:
            raise AttributeError("Unexpected attribute as text filter! {}".format(type(text)))

    def __init__(self, name=None, attrs=None, children=None, parent=None, text=None):
        """
        Condition class for filtering the XML parse events.
        If the condition satisfies the callback function will be called.
        :param name: Tag name. Can be str, regexp, bool callalble or a tuple of them.
        :param attrs: Attributes dict. The keys are names of attributes, values can be str, regexp, bool callalble
        and tuple of them.
        :param children: Optional filter for constrain child node(s). It is a Condition or a dict/tuple of arguments.
        :param parent: Optional filter for constrain parent node(s). It is a Condition or a dict/tuple of arguments.
        :param text: Text of the node. Can be str, regexp, bool callalble or a tuple of them.
        """
        self._and = Condition.normalize_condition(True)             # cond. must be match also
        self._or = Condition.normalize_condition(False)             # cond. if matches, self matches also
        self._inverted = False                                      # self doesn't matches if would be match
        self.check = self._check                                    # set the non-inverted check function
        # condition attributes (check callables will be created):
        self._name = Condition.normalize_name(name)
        self._attrs = Condition.normalize_attrs(attrs)
        self._text = Condition.normalize_text(text)
        self._children = Condition.normalize_condition(children, allow_parents=False)  # Nonsense check child's parent
        self._parent = Condition.normalize_condition(parent, allow_children=False)     # Cannot check siblings! (memory)

    def and_(self, *cond):
        self._and = Condition.normalize_condition(*cond)
        return self._and

    def or_(self, *cond):
        self._or = Condition.normalize_condition(*cond)
        return self._or

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

    def _check(self, element) -> bool:
        if not self._name(element.tag):                         # If tagname doesn't match, element cannot match
            return False
        if not self._attrs(element.attrib):                     # If attrs dict doesn't match, element doesn't match
            return False
        if not self._text(element.text):                        # If text doesn't match, element doesn't match
            return False

        # CSAK lxml.ElementTree todo: WORKAROUND
        if LXML:
            if not self._parent.check(element.getparent()):     # The parents will be checked recursivelly.
                return False

        for child in list(element):
            if self._children.check(child):                     # The children will be checked iterativelly.
                return True                                     # If any child matches, the condition matches.

        return False  # This can be occured only if every condition matched exept children.

    def _inverted_check(self, element) -> bool:
        return not self._check(element)

    def keep(self, element) -> bool:
        # todo
        return True


class CallbackRunner():
    ETREE = 1
    STRING = 2
    DICT = 3

    @staticmethod
    def _default():
        pass

    @staticmethod
    def _convert_to_string(e):
        return etree.tostring(e)

    @staticmethod
    def _convert_to_dict(e):
        # {tag: "", attrib: {}, text: "", children: []}
        d = {}
        d["tag"] = e.tag
        d["attrib"] = e.attrib
        d["text"] = e.text
        ch = []
        for child in list(e):
            ch.append(CallbackRunner._convert_to_dict(child))
        d["children"] = ch
        return d


    @staticmethod
    def _convert_to_element(e):
        return e

    def __init__(self, t: int):
        # todo: típus as property
        self._callback = CallbackRunner._default
        self._type = t
        if t == CallbackRunner.ETREE:
            self._convert = CallbackRunner._convert_to_element
        elif t == CallbackRunner.STRING:
            self._convert = CallbackRunner._convert_to_string
        elif t == CallbackRunner.DICT:
            self._convert = CallbackRunner._convert_to_dict
        else:
            raise AttributeError("CallbackRunner type must be one of CallbackRunner.ETREE, CallbackRunner.STRING and "
                                 "CallbackRunner.DICT!")

    def calls(self, callback):
        self._callback = callback

    def __call__(self, element, line: int=0):
        self._callback(self._convert(element), line)


class YAXReader():
    def __init__(self, stream: io.TextIOBase = None):
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
        """
        Start the parsing
        :param chunk_size:
        :return:
        """
        if not self._stream:
            raise AttributeError("Input stream is not initialized.")
        elif self._stream.closed:
            raise AttributeError("The input stream is closed.")

        def process_element(e):
            for cond, cb_runner in self._cnds:
                if cond.check(e):
                    cb_runner(e)
                if not cond.keep(e):
                    del e.getparent()[e.getparent().index(e)]

        parser = etree.XMLPullParser(events=('end',))
        chunk = self._stream.read(chunk_size)
        while not chunk == "":
            parser.feed(chunk)
            for action, element in parser.read_events():
                process_element(element)
            chunk = self._stream.read(chunk_size)

    def find_as_element(self, name=None, attrs={}, children=None, parent=None, text=None) -> CallbackRunner:
        """
        Define a filter for parsing.
        If the pending subtree matches the filter, the parser calls the given callback with the found XML chunk as
        an ElementTree.
        :param name: Tag name. Can be str, regexp, bool callalble or a tuple of them.
        :param attrs: Attributes dict. The keys are names of attributes, values can be str, regexp, bool callalble
        and tuple of them.
        :param children: Optional filter for constrain child node(s). It is a Condition or a dict/tuple of arguments.
        :param parent: Optional filter for constrain parent node(s). It is a Condition or a dict/tuple of arguments.
        :param text: Text of the node. Can be str, regexp, bool callalble or a tuple of them.
        :return: CallbackRunner object to connect with a callable.

        >>> reader.find_as_etree("BOTANICAL", parent={'children': Condition('PRICE', text=lambda x: float(x[1:]) < 5)}
        ).calls(lambda d: print(d.text))
        """
        tup = (Condition(name, attrs, children, parent, text), CallbackRunner(CallbackRunner.ETREE));
        self._cnds.append(tup)
        return tup[1]

    def find_as_str(self, name=None, attrs={}, children=None, parent=None, text=None) -> CallbackRunner:
        """
        Define a filter for parsing.
        If the pending subtree matches the filter, the parser calls the given callback with the found XML chunk as
        an str.
        :param name: Tag name. Can be str, regexp, bool callalble or a tuple of them.
        :param attrs: Attributes dict. The keys are names of attributes, values can be str, regexp, bool callalble
        and tuple of them.
        :param children: Optional filter for constrain child node(s). It is a Condition or a dict/tuple of arguments.
        :param parent: Optional filter for constrain parent node(s). It is a Condition or a dict/tuple of arguments.
        :param text: Text of the node. Can be str, regexp, bool callalble or a tuple of them.
        :return: CallbackRunner object to connect with a callable.

        >>> reader.find_as_str("BOTANICAL", parent={'children': Condition('PRICE', text=lambda x: float(x[1:]) < 5)}
        ).calls(lambda s: print(s))
        """
        tup = (Condition(name, attrs, children, parent, text), CallbackRunner(CallbackRunner.STRING));
        self._cnds.append(tup)
        return tup[1]

    def find_as_dict(self, name=None, attrs={}, children=None, parent=None, text=None) -> CallbackRunner:
        """
        Define a filter for parsing.
        If the pending subtree matches the filter, the parser calls the given callback with the found XML chunk as
        a dict.
        :param name: Tag name. Can be str, regexp, bool callalble or a tuple of them.
        :param attrs: Attributes dict. The keys are names of attributes, values can be str, regexp, bool callalble
        and tuple of them.
        :param children: Optional filter for constrain child node(s). It is a Condition or a dict/tuple of arguments.
        :param parent: Optional filter for constrain parent node(s). It is a Condition or a dict/tuple of arguments.
        :param text: Text of the node. Can be str, regexp, bool callalble or a tuple of them.
        :return: CallbackRunner object to connect with a callable.

        >>> reader.find_as_dict("BOTANICAL", parent={'children': Condition('PRICE', text=lambda x: float(x[1:]) < 5)}
        ).calls(lambda d: print(d['text']))
        """
        tup = (Condition(name, attrs, children, parent, text), CallbackRunner(CallbackRunner.DICT));
        self._cnds.append(tup)
        return tup[1]

    def match_as_element(self, cond: Condition) -> CallbackRunner:
        """
        Define a filter for parsing.
        If the pending subtree matches the condition, the parser calls the given callback with the found XML chunk as
        an ElementTree.
        :param cond: Condition
        :return: CallbackRunner object to connect with a callable.

        >>> reader.match_as_etree(condition).calls(lambda d: print(d.text))
        """
        tup = (cond, CallbackRunner(CallbackRunner.ETREE));
        self._cnds.append(tup)
        return tup[1]

    def match_as_str(self, cond: Condition) -> CallbackRunner:
        """
        Define a filter for parsing.
        If the pending subtree matches the condition, the parser calls the given callback with the found XML chunk as
        an str.
        :param cond: Condition
        :return: CallbackRunner object to connect with a callable.

        >>> reader.match_as_str(condition).calls(lambda d: print(d))
        """
        tup = (cond, CallbackRunner(CallbackRunner.STRING));
        self._cnds.append(tup)
        return tup[1]

    def match_as_dict(self, cond: Condition) -> CallbackRunner:
        """
        Define a filter for parsing.
        If the pending subtree matches the condition, the parser calls the given callback with the found XML chunk as
        a dict.
        :param cond: Condition
        :return: CallbackRunner object to connect with a callable.

        >>> reader.match_as_dict(condition).calls(lambda d: print(d['text']))
        """
        tup = (cond, CallbackRunner(CallbackRunner.DICT));
        self._cnds.append(tup)
        return tup[1]