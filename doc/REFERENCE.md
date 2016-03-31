# Reference

## Module: yax
```python
import yax
```
It contains and loads all of the following classes and functions.
## Classes
#### YAXReader
```python
yr = yax.YAXReader(stream=None, use_lxml=False)
```
This class presents the main functionality and interface of library.
* *stream*: Text input source. It is a TextIOWrapper object, eg. an `open("filename")` expression.
    After the analysis is performed, it will be closed.
* *use_lxml*: LXML library will be used as back-end if available.

##### Methods:
```python
yr.lxml_in_use() -> bool
```
tells, whether lxml module is used. If we initialized the YAXReader with `use_lxml=True` however,
it is unavailable, YAX uses the built-in xml module and this method returns with `False`.

```python
yr.find(tag=None, attrib=None, text=None, parent=None, children=None, keep_children=None) -> CallbackRunner
```
is the function to define event handlers. It creates a filter and when a subtree fultils them,
it performs the event-handler.
You can specify the subtree filter with the following arguments:
* *tag*: Condition for the tag name content, can be a string, a compiled regexp a bool callable
    (eg. lambda) or a list of them. If it is a list, the condition is satisfied when one of the
    list items is satisfied. If it is None, it is always satisfied.
* *attrib*: Dict object as the condition for the attributes.
    Keys must be str, values can be like the tag argument. It also can be True when we want to check
    only the existance of the specified attribute.
* *text*: Condition for the text content, can be a string, a compiled regexp a bool callable
    (eg. lambda) or a list of them. If it is a list, the condition is satisfied when one of the
    list items is satisfied. If it is None, it is always satisfied.
* *parent*: Condition for the element's parent. It can be a Condition object as well as a dict whith
    the condition argument keys or a tuple wiht well ordered arguments.
    We cannot check the siblings because of the restrictions of the xml module.
* *children*: Condition for the element's children. It can be a Condition object as well as a dict whith
    the condition argument keys, like `{"tag": "a", "attrib": {"href": True}}` or a tuple wiht well ordered arguments.
* *keep_children*: Condition for children which have to be kept in the memory but are not specified above.

Returns a `CallbackRunner` object, which can run a callabble with the found subtree.

```python
yr.match(cond: Condition) -> CallbackRunner
```
is the function to define event handlers. It creates a filter and when a subtree fultils them,
it performs the event-handler.
You can specify the subtree filter with the initialized `Condition` object.

```python
yr.start()
```
performs the analysis and closes the stream at the end of that.

##### Examples:
```python
import yax
import re

yr = yax.YAXReader(open("flowers.xml"))
yr.find("flower", children={"tag": "price", "text": lambda p: float(p) < 10})
    .calls(lambda e, l: print("Cheap flower: {}".format(e.find("name").text)))
yr.find("flower", children={"tag": "price", "text": lambda p: float(p) > 10})
    .calls(lambda e, l: print("Expensive flower: {}".format(e.find("name").text)))
yr.find("flower", children=(re.compile("colou?r"), None, ["yellow", "orange", "red", "purple"]))
    .calls(lambda e, l: print("The {} is nice!".format(e.find("name").text)))
yr.start()
```
This example shows how a YAXReader object can be set with more subtree condition.
As you can see the tag argument also can be a regex and the childen condition can be a dict or a tuple, too.

#### Condition

#### CallbackRunner
This class is instantiated when the `YAXReader.find` or the `YAXReader.mach` methods are called.
You cannot instantiate it directly. It contains a callback object which is called when the
preset condition is satisfied.
```python
cr = yr.find("a", {"href": True})
```
##### Methods:
```python
cr.calls(callback)
```
sets the callback object for them.
It is a callable object with at least 2 arguments (the subtree element itself and the line number).

```python
cr.inverted()
```
returns the CallbackRunner object itself but inverts the defined condition. It means that it calls the callback if the original condition would not call them.
##### Examples:
```python
yr.find("a", {"href": True}).calls(lambda e, l: print(e.text))
```
This example shows how the callback object (a lambda in this case) can be set.
