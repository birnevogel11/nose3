"""nose unittest.TestCase subclasses. It is not necessary to subclass these
classes when writing tests; they are used internally by nose.loader.TestLoader
to create test cases from test functions and methods in test classes.
"""
import logging
import unittest
from nose.util import try_run

log = logging.getLogger(__name__)

# FIXME probably not the best name, since it is mainly used for errors
class Failure(unittest.TestCase):
    def __init__(self, exc_class, exc_val, tb=None):
        print "A failure! %s %s" % (exc_class, exc_val)
        self.exc_class = exc_class
        self.exc_val = exc_val
        self.tb = tb
        unittest.TestCase.__init__(self)

    def runTest(self):
        if self.tb:
            raise self.exc_class, self.exc_val, self.tb
        else:
            raise self.exc_class(self.exc_val)


class Test(unittest.TestCase):
    """The universal contextualized test case wrapper.

    When you see a test, as a runner or a plugin, you will always see
    an instance of this class.
    """
    # FIXME implement startTest and stopTest so those can be passed
    # to plugins and output capture can be started and stopped
    def __init__(self, context, test):
        print "Test %s %s" % (context, test)
        self.context = context
        self.test = test
        unittest.TestCase.__init__(self)
        
    def __call__(self, *arg, **kwarg):
        print "Test call %s %s %s" % (self, arg, kwarg)
        return self.run(*arg, **kwarg)

    def __str__(self):
        return str(self.test)

    def id(self):
        return self.test.id()

    def setUp(self):
        print "Test setup %s" % self
        self.context.setup(self.test)

    def run(self, result):
        # FIXME wrap result in my configured result proxy
        # to capture stdout, etc. The result proxy also needs
        # to differentiate between nose.case.Test and other test types
        # since result.startTest, etc, are all going to be called
        # multiple times for each test.
        self.result = result
        unittest.TestCase.run(self, result)
        
    def runTest(self):
        # FIXME pass in a result with mock start/stop since
        # start/stop has already been called by self
        self.test(self.result)

    def shortDescription(self):
        return self.test.shortDescription()

    def tearDown(self):
        print "Test teardown %s" % self
        self.context.teardown(self.test)
        

class FunctionTestCase(unittest.TestCase):
    """TestCase wrapper for functional tests.

    Don't use this class directly; it is used internally in nose to
    create test cases for functional tests.
    
    This class is very similar to unittest.FunctionTestCase, with a few
    extensions:
      * The test descriptions are disambiguated by including the full
        module path when a test with a similar name has been seen in
        the test run. 
      * It allows setup and teardown functions to be defined as attributes
        of the test function. A convenient way to set this up is via the
        provided with_setup decorator:

        def setup_func():
            # ...

        def teardown_func():
            # ...
        
        @with_setup(setup_func, teardown_func)        
        def test_something():
            # ...

    """
    _seen = {}
    
    def __init__(self, test, setUp=None, tearDown=None, arg=tuple(),
                 descriptor=None):
        self.test = test
        self.setUpFunc = setUp
        self.tearDownFunc = tearDown
        self.arg = arg
        self.descriptor = descriptor
        # FIXME restore the 'fromDirectory' setting -- find the base
        # of the package containing the module containing the testFunc
        unittest.TestCase.__init__(self)
        
    def id(self):
        return str(self)
    
    def runTest(self):
        self.test(*self.arg)
        
    def setUp(self):
        """Run any setup function attached to the test function
        """
        if self.setUpFunc:
            self.setUpFunc()
        else:
            names = ('setup', 'setUp', 'setUpFunc')
            try_run(self.test, names)

    def tearDown(self):
        """Run any teardown function attached to the test function
        """
        if self.tearDownFunc:
            self.tearDownFunc()
        else:
            names = ('teardown', 'tearDown', 'tearDownFunc')
            try_run(self.test, names)
        
    def __str__(self):
        func, arg = self._descriptors()
        self.fromDirectory = 'FIXME'
        if hasattr(func, 'compat_func_name'):
            name = func.compat_func_name
        else:
            name = func.__name__
        name = "%s.%s" % (func.__module__, name)
        if arg:
            name = "%s%s" % (name, arg)

        if self._seen.has_key(name) and self.fromDirectory is not None:
            # already seen this exact test name; put the
            # module dir in front to disambiguate the tests
            name = "%s: %s" % (self.fromDirectory, name)
        self._seen[name] = True
        return name 
    __repr__ = __str__
    
    def shortDescription(self):
        func, arg = self._descriptors()
        doc = getattr(func, '__doc__', None)
        if not doc:
            doc = str(self)
        return doc.split("\n")[0].strip()

    def _descriptors(self):
        """Get the descriptors of the test function: the function and
        arguments that will be used to construct the test name. In
        most cases, this is the function itself and no arguments. For
        tests generated by generator functions, the original
        (generator) function and args passed to the generated function
        are returned.
        """
        if self.descriptor:
            return self.descriptor, self.arg
        else:            
            return self.test, self.arg


# FIXME this is just a minimal working version
# need to add fixture support
class MethodTestCase(unittest.TestCase):

    def __init__(self, method, test=None, arg=tuple(), descriptor=None):
        """Initialize the MethodTestCase.

        Required argument:

        * method -- the method to call, may be bound or unbound. In either
        case, a new instance of the method's class will be instantiated to
        make the call.

        Optional arguments:

        * test -- the test function to call. If this is passed, it will be
        called instead of getting a new bound method of the same name as the
        desired method from the test instance. This is to support generator
        methods that yield inline functions.

        """
        print "Make a MethodTestCase for %s" % method
        self.method = method
        self.test = test
        self.arg = arg
        self.descriptor = descriptor
        self.cls = method.im_class
        self.inst = self.cls()
        if self.test is None:
            method_name = self.method.__name__
            self.test = getattr(self.inst, method_name)            
        unittest.TestCase.__init__(self)

    def setUp(self):
        try_run(self.inst, ('setup', 'setUp'))
        
    def runTest(self):
        self.test(*self.arg)

    def tearDown(self):
        try_run(self.inst, ('teardown', 'tearDown'))
        
    def _descriptors(self):
        """Get the descriptors of the test method: the method and
        arguments that will be used to construct the test name. In
        most cases, this is the method itself and no arguments. For
        tests generated by generator methods, the original
        (generator) method and args passed to the generated method 
        or function are returned.
        """
        if self.descriptor:
            return self.descriptor, self.arg
        else:
            return self.method, self.arg
        

# old
## class MethodTestCase(unittest.TestCase):
##     """Test case that wraps one method in a test class.
##     """    
##     def __init__(self, cls, method, method_desc=None, *arg):
##         self.cls = cls
##         self.method = method
##         self.method_desc = method_desc
##         self.testInstance = self.cls()
##         self.testCase = getattr(self.testInstance, method)
##         self.arg = arg
##         log.debug('Test case: %s%s', self.testCase, self.arg)        
##         unittest.TestCase.__init__(self)
        
##     def __str__(self):
##         return self.id()

##     def desc(self):
##         if self.method_desc is not None:
##             desc = self.method_desc
##         else:
##             desc = self.method
##         if self.arg:
##             desc = "%s:%s" % (desc, self.arg)
##         return desc

##     def id(self):
##         return "%s.%s.%s" % (self.cls.__module__,
##                              self.cls.__name__,
##                              self.desc())

##     def setUp(self):
##         """Run any setup method declared in the test class to which this
##         method belongs
##         """
##         names = ('setup', 'setUp')
##         try_run(self.testInstance, names)

##     def runTest(self):
##         self.testCase(*self.arg)
        
##     def tearDown(self):
##         """Run any teardown method declared in the test class to which
##         this method belongs
##         """
##         if self.testInstance is not None:
##             names = ('teardown', 'tearDown')
##             try_run(self.testInstance, names)

##     def shortDescription(self):
##         # FIXME ... diff output if is TestCase subclass, for back compat
##         if self.testCase.__doc__ is not None:            
##             return '(%s.%s) "%s"' % (self.cls.__module__,
##                                      self.cls.__name__,
##                                      self.testCase.__doc__)
##         return None
        
        
