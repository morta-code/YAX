import re

__author__ = 'Móréh, Tamás'

RE = type(re.compile(""))


class ConditionException(Exception):
    pass


class CheckListItems:
    def __init__(self, callables: list):
        self.callables = callables

    def __call__(self, t):
        for tag_cond in self.callables:
            if tag_cond(t):
                return True
        return False


class CheckAttrib:
    def __init__(self, attrib: dict):
        self.attrib = attrib

    def __call__(self, attr):
        for key, check in self.attrib.items():
            val = attr.get(key)
            if not check(val):
                return False
        return True


class EmptyCondition:
    def __init__(self, b: bool):
        self._return_default = b

    def check(self, *_):
        return self._return_default


class Condition:

    LXML = False

    """
    Condition class for filtering the XML parse events.
    If the condition satisfies the callback function will be called.
    """

    @staticmethod
    def normalize_condition(cnd, allow_parents=True, allow_children=True, none_answer=True,
                            allow_none=True):
        """
        Converts all possible condition input to a valid condition
        :param cnd: Condition, EmptyCondition or tag-filter type
        :param allow_parents: condition can have condition for its parent
        :param allow_children: condition can have condition for its children
        :param none_answer: the default result of EmptyCondition when cnd is None
        :param allow_none:
        :return: a valid Condition object
        :raises ConditionException: if the cnd cannot be converted to a valid Condition
        """
        def check_child(cc):
            if not allow_children:
                if len(cc._children) != 0:
                    raise ConditionException("Checking children of parents not allowed!")

        def check_parent(cp):
            if not allow_parents:
                if not isinstance(cp._parent, EmptyCondition):
                    raise ConditionException("Checking parents of child not allowed!")

        if isinstance(cnd, Condition):
            check_child(cnd)
            check_parent(cnd)
            return cnd
        if isinstance(cnd, EmptyCondition):
            return cnd
        if isinstance(cnd, (str, RE, list)):
            return Condition(cnd)
        if isinstance(cnd, bool):
            return EmptyCondition(cnd)
        if cnd is None and allow_none:
            return EmptyCondition(none_answer)
        if isinstance(cnd, dict):
            c = Condition(cnd.get('tag'), cnd.get('attrib'), cnd.get('text'),
                          cnd.get('parent'), cnd.get('children'), cnd.get("keep_children"))
            check_child(c)
            check_parent(c)
            return c
        if isinstance(cnd, tuple):
            if len(cnd) == 0:
                return EmptyCondition(none_answer)
            c = Condition(*cnd)
            check_child(c)
            check_parent(c)
            return c
        raise ConditionException("Invalid type as condition! {}".format(type(cnd)))

    @staticmethod
    def normalize_children(cnd) -> list:
        if cnd is None:
            return []
        if isinstance(cnd, list):
            return [Condition.normalize_condition(c, allow_parents=False, allow_none=False)
                    for c in cnd]
        else:
            return [Condition.normalize_condition(cnd, allow_parents=False, allow_none=False), ]

    @staticmethod
    def normalize_tag(tag, firstlevel=True):
        """
        Converts all possible tag-condition definition to a callable object.
        :param tag: Condition for tag name/text content, can be str, compiled regexp or list of
        them. It can be also True and None. None condition will be always satisfied, True if the
        tag/text exists.
        :param firstlevel: A flag for this recursive function. Do not use directly!
        :return: a callable object which returns True iff the condition satisfied
        """
        if callable(tag):  # A (hopefully) bool expression
            return tag
        elif isinstance(tag, str):  # The lam.expr. will compare
            return lambda s: s == tag
        elif isinstance(tag, RE):  # The l.exp. checks with fullmatch
            # return lambda s: s is not None and tag.fullmatch(s) is not None
            return lambda s: tag.fullmatch(s) is not None
        elif isinstance(tag, list) and firstlevel:  # The l.ex. checks the containing
            return CheckListItems([Condition.normalize_tag(t, firstlevel=False) for t in tag])
        elif tag is True and firstlevel:  # True only if exists. Only for text is relevant.
            return lambda s: not not s
        elif tag is None and firstlevel:  # If none, everything will be accepted.
            return lambda s: True
        else:
            raise ConditionException("Invalid parameter as tag/text name filter! {}".
                                     format(type(tag)))

    @staticmethod
    def normalize_attrib(attrib):
        """
        Converts the attribute-condition definition to a callable object.
        :param attrib: attribute-condition dict. Keys must be str, values can be str, compiled
        regexp or list of them. It can be also True and it's satisfied if the attribute exists.
        :return: a callable object which returns True iff the condition satisfied
        """
        if not attrib:  # Empty dict or None accepts everything.
            return lambda d: True
        elif isinstance(attrib, dict):
            return CheckAttrib({k: Condition.normalize_tag(v) for k, v in attrib.items()})
        else:
            raise ConditionException("Invalid parameter as attribute filter! {}".
                                     format(type(attrib)))

    def __init__(self, tag=None, attrib=None, text=None,
                 parent=None, children=None, keep_children=None):

        self._inverted = False  # self doesn't matches if would be match

        # The LXML way has different methods:
        if Condition.LXML:
            self.check = self._check_lxml
            self.keep = self._keep_lxml
            self._check_children = self._check_children_lxml
        else:
            self.check = self._check_xml
            self.keep = self._keep_xml
            self._check_children = self._check_children_xml

        # condition attributes (check callables will be created):
        self._tag = Condition.normalize_tag(tag)
        self._attrib = Condition.normalize_attrib(attrib)
        self._text = Condition.normalize_tag(text)
        self._parent = Condition.normalize_condition(parent, allow_children=False)
        self._children = Condition.normalize_children(children)
        self._keep = Condition.normalize_children(keep_children)

    def inverse(self):
        """
        Negate the current condition
        :return: The negated condition itself.
        """
        self._inverted = not self._inverted
        if self._inverted:
            self.check = self._inverted_check_lxml if Condition.LXML \
                else self._inverted_check_xml
        else:
            self.check = self._check_lxml if Condition.LXML \
                else self._check_xml
        return self

    def _check_children_lxml(self, element):
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

    def _check_children_xml(self, element):
        children = list(element)  # Every child-condition must be matching to a
        for ch_cond in self._children:  # child
            found = False
            for child in children:
                if ch_cond.check(child, []):  # There is no way to check children's parents!
                    found = True
                    break
            if not found:
                return False
        return True

    def _check_lxml(self, element) -> bool:
        try:
            # If any part of condition is false, return with false.
            if not self._tag(element.tag):                          # Checking tagname
                return False
            if not self._attrib(element.attrib):                    # Checking attribs
                return False
            if element.text is None:                                # Checking text
                if not self._text(None):
                    return False
            else:
                if not self._text(element.text.strip()):
                    return False
            if not self._parent.check(element.getparent()):     # Checking parent
                return False
            if not self._check_children(element):                   # Checking children
                return False
        except:
            return False
        return True

    def _check_xml(self, element, parents) -> bool:
        try:
            # If any part of condition is false, return with false.
            if not self._tag(element.tag):                          # Checking tagname
                return False
            if not self._attrib(element.attrib):                    # Checking attribs
                return False
            if element.text is None:                                # Checking text
                if not self._text(None):
                    return False
            else:
                if not self._text(element.text.strip()):
                    return False
            if not self._parent.check(parents[-1] if len(parents) > 0 else None, parents[:-1]):
                    return False
            if not self._check_children(element):                   # Checking children
                return False
        except:
            return False
        return True

    def _inverted_check_lxml(self, element) -> bool:
        return not self._check_lxml(element)

    def _inverted_check_xml(self, element, parents) -> bool:
        return not self._check_xml(element, parents)

    def _keep_lxml(self, element) -> bool:
        parent = element.getparent()
        if parent is None:
            return True
        if not self._tag(parent.tag):     # Element's parent must be match
            return False
        for ch_cond in self._children:                  # Keep if it is in the children conditions
            if ch_cond.check(element):
                return True
        for keep_cond in self._keep:                    # Keep if it is in the keep conditions
            if keep_cond.check(element):
                return True
        return False

    def _keep_xml(self, element, parents) -> bool:
        if not len(parents) > 0:
            return True
        if not self._tag(parents[-1].tag):     # Element's parent must be match
            return False
        for ch_cond in self._children:                  # Keep if it is in the children conditions
            if ch_cond.check(element, parents):
                return True
        for keep_cond in self._keep:                    # Keep if it is in the keep conditions
            if keep_cond.check(element, parents):
                return True
        return False
