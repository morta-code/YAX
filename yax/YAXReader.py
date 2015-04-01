import io
import re

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

        def check(self):
            # todo: cizellálni kell egy kicsit
            return self._return_default

    @staticmethod
    def normalize_condition(cnd):
        if isinstance(cnd, bool):
            return Condition.EmptyCondition(cnd)
        elif cnd is None:
            return Condition.EmptyCondition(True)
        elif isinstance(cnd, (Condition, Condition.EmptyCondition)):
            return cnd
        elif isinstance(cnd, dict):
            return Condition(cnd.get('name'), cnd.get('attrs'), cnd.get('children'), cnd.get('parent'), cnd.get('text'))
        elif isinstance(cnd, (tuple, list)):
            return Condition(cnd[0], cnd[1], cnd[2], cnd[3], cnd[4])
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
        # condition attributes (check callables will be created):
        self._name = Condition.normalize_name(name)
        self._attrs = Condition.normalize_attrs(attrs)
        self._text = Condition.normalize_text(text)
        self._children = Condition.normalize_condition(children)
        self._parent = Condition.normalize_condition(parent)

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
        return self

    def check(self, element):
        self._name(element.tag)
        self._attrs(element.attrib)
        self._text(element.text)
        # CSAK lxml.ElementTree
        if LXML:
            self._parent.check(element.getparent())
        for child in list(element):
            self._children.check(child)
        # todo: kiértékelés


class CallbackRunner():
    ETREE = 1
    STRING = 2
    DICT = 3

    @staticmethod
    def _default():
        pass

    def __init__(self, t: int):
        self._type = t
        self._callback = CallbackRunner._default

    def calls(self, callback):
        self._callback = callback

    def __call__(self, *params):
        # todo: milyen formátumú a params? (chunk, hol?)
        self._callback(*params)


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

    def start(self):
        """
        Start the parsing
        """
        if not self._stream:
            raise AttributeError("Input stream is not initialized.")
        elif self._stream.closed:
            raise AttributeError("The input stream is closed.")

        raise NotImplementedError("TODO")
        pass  # todo

    def find_as_etree(self, name=None, attrs={}, children=None, parent=None, text=None) -> CallbackRunner:
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

    def match_as_etree(self, cond: Condition) -> CallbackRunner:
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