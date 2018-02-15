"""Tests for super()."""


from pytype import utils
from pytype.tests import test_base


class SuperTest(test_base.BaseTest):
  """Tests for super()."""

  def testSetAttr(self):
    self.Check("""
      class Foo(object):
        def foo(self, name, value):
          super(Foo, self).__setattr__(name, value)
    """)

  def testStr(self):
    self.Check("""
      class Foo(object):
        def foo(self, name, value):
          super(Foo, self).__str__()
    """)

  def testGet(self):
    self.Check("""
      class Foo(object):
        def foo(self, name, value):
          super(Foo, self).__get__(name)
    """)

  def testInheritedGet(self):
    self.Check("""
      class Foo(object):
        def __get__(self, obj, objtype):
          return 42
      class Bar(Foo):
        def __get__(self, obj, objtype):
          return super(Bar, self).__get__(obj, objtype)
      class Baz(object):
        x = Bar()
      Baz().x + 1
    """)

  def testInheritedGetGrandparent(self):
    self.Check("""
      class Foo(object):
        def __get__(self, obj, objtype):
          return 42
      class Mid(Foo):
        pass
      class Bar(Mid):
        def __get__(self, obj, objtype):
          return super(Bar, self).__get__(obj, objtype)
      class Baz(object):
        x = Bar()
      Baz().x + 1
    """)

  def testInheritedGetMultiple(self):
    self.Check("""
      class Foo(object):
        def __get__(self, obj, objtype):
          return 42
      class Quux(object):
        pass
      class Bar(Quux, Foo):
        def __get__(self, obj, objtype):
          return super(Bar, self).__get__(obj, objtype)
      class Baz(object):
        x = Bar()
      Baz().x + 1
    """)

  def testSet(self):
    _, errors = self.InferWithErrors("""\
      class Foo(object):
        def foo(self, name, value):
          super(Foo, self).__set__(name, value)
    """)
    self.assertErrorLogIs(errors, [(3, "attribute-error", r"__set__.*super")])

  def testInheritedSet(self):
    self.Check("""
      class Foo(object):
        def __init__(self):
          self.foo = 1
        def __set__(self, name, value):
          self.foo = value
      class Bar(Foo):
        def __set__(self, name, value):
          super(Bar, self).__set__(name, value)
      class Baz():
        x = Bar()
      y = Baz()
      y.x = 42
    """)

  def testInit(self):
    self.Check("""
      class Foo(object):
        def foo(self, name, value):
          super(Foo, self).__init__()
    """)

  def testGetAttr(self):
    self.Check("""
      class Foo(object):
        def hello(self, name):
          getattr(super(Foo, self), name)
    """)

  def testGetAttrMultipleInheritance(self):
    self.Check("""
      class X(object):
        pass

      class Y(object):
        bla = 123

      class Foo(X, Y):
        def hello(self):
          getattr(super(Foo, self), "bla")
    """)

  def testGetAttrInheritance(self):
    self.Check("""
      class Y(object):
        bla = 123

      class Foo(Y):
        def hello(self):
          getattr(super(Foo, self), "bla")
    """)

  def testIsInstance(self):
    self.Check("""
      class Y(object):
        pass

      class Foo(Y):
        def hello(self):
          return isinstance(super(Foo, self), Y)
    """)

  def testCallSuper(self):
    _, errorlog = self.InferWithErrors("""\
      class Y(object):
        pass

      class Foo(Y):
        def hello(self):
          return super(Foo, self)()
    """)
    self.assertErrorLogIs(errorlog, [(6, "not-callable", r"super")])

  def testSuperType(self):
    ty = self.Infer("""
      class A(object):
        pass
      x = super(type, A)
    """)
    self.assertTypesMatchPytd(ty, """
      class A(object):
        pass
      x = ...  # type: super
    """)

  def testSuperWithAmbiguousBase(self):
    with utils.Tempdir() as d:
      d.create_file("foo.pyi", """
        class Grandparent(object):
          def f(self) -> int
      """)
      ty = self.Infer("""
        import foo
        class Parent(foo.Grandparent):
          pass
        OtherParent = __any_object__
        class Child(OtherParent, Parent):
          def f(self):
            return super(Parent, self).f()
      """, pythonpath=[d.path])
      self.assertTypesMatchPytd(ty, """
        from typing import Any
        foo = ...  # type: module
        class Parent(foo.Grandparent): ...
        OtherParent = ...  # type: Any
        class Child(Any, Parent): ...
      """)

  def testSuperWithAny(self):
    self.Check("""
      super(__any_object__, __any_object__)
    """)

  def testSingleArgumentSuper(self):
    _, errors = self.InferWithErrors("""\
      super(object)
      super(object())
    """)
    self.assertErrorLogIs(
        errors, [(2, "wrong-arg-types", r"cls: type.*cls: object")])

  def testMethodOnSingleArgumentSuper(self):
    ty, errors = self.InferWithErrors("""\
      sup = super(object)
      sup.foo
      sup.__new__(object)
      v = sup.__new__(super)
    """)
    self.assertTypesMatchPytd(ty, """
      sup = ...  # type: super
      v = ...  # type: super
    """)
    self.assertErrorLogIs(errors, [
        (2, "attribute-error", r"'foo' on super"),
        (3, "wrong-arg-types", r"Type\[super\].*Type\[object\]")])

  def testSuperMissingArg(self):
    _, errors = self.InferWithErrors("""\
      class Foo(object):
        def __new__(cls):
          return super(cls).__new__(cls)
      class Bar(object):
        def __new__(cls):
          return super().__new__(cls)
    """)
    self.assertErrorLogIs(errors, [
        (3, "wrong-arg-types", r"Type\[super\].*Type\[Foo\]"),
        (6, "wrong-arg-count", r"2.*0")])

  def testSuperUnderDecorator(self):
    self.Check("""\
      def decorate(cls):
        return __any_object__
      class Parent(object):
        def Hello(self):
          pass
      @decorate
      class Child(Parent):
        def Hello(self):
          return super(Child, self).Hello()
    """)

  def testSuperSetAttr(self):
    _, errors = self.InferWithErrors("""\
      class Foo(object):
        def __init__(self):
          super(Foo, self).foo = 42
    """)
    self.assertErrorLogIs(errors, [(3, "not-writable", r"super")])

  def testSuperSubclassSetAttr(self):
    _, errors = self.InferWithErrors("""\
      class Foo(object): pass
      class Bar(Foo):
        def __init__(self):
          super(Bar, self).foo = 42
    """)
    self.assertErrorLogIs(errors, [(4, "not-writable", r"super")])

  def testSuperNothingSetAttr(self):
    with utils.Tempdir() as d:
      d.create_file("foo.pyi", """
        class Foo(nothing): ...
      """)
      _, errors = self.InferWithErrors("""\
        import foo
        class Bar(foo.Foo):
          def __init__(self):
            super(foo.Foo, self).foo = 42
      """, pythonpath=[d.path])
      self.assertErrorLogIs(errors, [(4, "not-writable", r"super")])

  def testSuperAnySetAttr(self):
    _, errors = self.InferWithErrors("""\
      class Foo(__any_object__):
        def __init__(self):
          super(Foo, self).foo = 42
    """)
    self.assertErrorLogIs(errors, [(3, "not-writable", r"super")])


if __name__ == "__main__":
  test_base.main()
