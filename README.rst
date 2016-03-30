===
YAX
===

**Yet Another XML parser** is a powerful event-based memory-efficient Python module.
It analyses the XML stream node by node and builds subtrees only if it is really needed.

In case of record-oriented XML input (when some subtree structure is repeated many times),
it processes the file in a sequential manner similar to that of *SAX*.
However, conditions can be defined which trigger a *DOM* like processing where subtrees are created.

This method is also efficient on very large data (which do not fit into the memory)
both in terms of storage and computational time complexity.

Dependencies
~~~~~~~~~~~~
YAX uses Python 3.x and above. It doesn't depend on any third party module.
However, if you have *lxml* installed you can use it as back-end.
(See the documentation about performance.)

Installation
~~~~~~~~~~~~
* Download as a zip archive, uncompress and use it.
* ``pip3 install yax``
* (Soon...) Downolad the deb package and install it.

Usage
~~~~~
A simple example which prints all the elements with tagname "a" and containing "href" attribute:

.. code:: python

    import yax

    yr = yax.YAXReader(open("file.xml"))
    yr.find("a", {"href": True}).calls(
        lambda e, i: print(yax.element_to_string(e, with_tail=False))  # with_tail only whith lxml!
    )
    yr.start()

A bit more complex example which filters a gpx record.
It prints the elevation values of the trackpoints in a specified area:

.. code:: python

    import yax

    yr = yax.YAXReader(open("route.gpx"))
    yr.find("trkpt", {"lat": lambda v: 47 < float(v) < 48,
                      "lon": lambda v: 16 < float(v) < 17},
            keep_children="ele"
            ).calls(lambda e, i: print(e.find("ele").text))
    yr.start()

This example shows that it would be erease all unneccessary children from the subtree
to save memory but in this case we need the child called "ele".
For more example or the complete reference see the documentation.

See also
~~~~~~~~

* `External documentation <doc/REFERENCE.md>`_
* `Issue tracker <https://github.com/morta-code/YAX/issues>`_ (feel free to use it!)