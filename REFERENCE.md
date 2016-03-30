# Reference

## Class: YAXReader
```python
class yax.YAXReader(stream=None, use_lxml=True)
```
This class presents the main functionality and interface of library.
* *stream*: Text input source. A TextIOWrapper object.
* *use_lxml*: Use LXML for back-end if available. (Not always better!)
### fields and functions
```python
lxml_in_use() -> bool
```
Returns True if `lxml` is loaded and used.
```python
find_as_element(tag=None, attrib={}, text=None, parent=None, children=None, keep_children=None) -> CallbackRunner
```
It creates and returns an event-handler object witch runs