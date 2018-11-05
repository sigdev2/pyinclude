Lazy calculations for Python
===================================

This Python module realize part of lazy calculations in functional programing paradigm, based on iterators.

Main part of module is class IteratorEx
______________________________

Relised base commands to work with list of items:
 - filter - for filter iterable object items
 - map - for map iterable object items
 - groupLiner - for join items to one in items sequance
 - group - for join items by many states to one in items sequance

To calculate result of commands list use:
 - reduce - set all items to one output accomulator
 - value - push items one by one to output function
 - join - join all items to one returned item

Functions
________

 - lazy_stateTable - convert python list-dict with state machine to library format lambda function from group and groupLiner methods
 - lazy_stringStates - convert list of string tokens to library format lambda function from group and groupLiner methods for tokenize strings
 - lazy - main function to decarate build in collections (list, str) to iterable lazy object
 - lazy_tokenize - macro function for create with iterable lazy object for str array of tokens

Example
_______

Base use:

.. code:: python

    import lazy

    text = r''' tes/*t t'*/e'xt /*h'g/*'jgh*/ j' kjhkj /* hlkjlkj 'hk*/jh'''
    lo = leazy(text)

Use methods:

.. code:: python

    lo.map(lambda x : x + ' ')

.. code:: python

    lo.filter(lambda x : False)

.. code:: python

    lo.group(lazy.lazy_stateTable(
        [
            [r'"', { r'none' : r'string', r'string' : r'none' }],
            ['\'', { r'none' : r'onestring', r'onestring' : r'none' }],
            ['\'\'\'', { r'none' : r'treeonestring', r'treeonestring' : r'none' }],
            [r'"""', { r'none' : r'treestring', r'treestring' : r'none' }],
            [r'/*', { r'none' : r'multi'}],
            [r'*/', { r'multi' : r'none'}],
            [r'//', { r'none' : r'single' }],
            [r'#', { r'none' : r'directive' }],
            ['\n', { r'single' : r'none', r'directive' : r'none' }]
        ])
