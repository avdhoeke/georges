Using and executing Georges
===========================

You can access the library by simply importing it:

    import georges

This will include only the core components of Georges. The different Georges' modules must be imported separately, depending on your needs:

    import georges.madx
    import georges.bdsim
    import georges.manzoni
    import georges.plotting

See the examples below for a typical use case.

    import georges
    from georges.plotting import *
    import georges.manzoni