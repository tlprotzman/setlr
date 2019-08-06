import unittest
import re
import io

from setlr import iterparse_filter

#### An incomplete test suite ####

class TestIterparseFilter(unittest.TestCase):
    def _test_path(self, path, args):
        #print "**** test_path", repr(path), repr(args)
        pattern = iterparse_filter.to_regexp(path)
        pat = re.compile(pattern)
        s = "/" + ("/".join(args)) + "/"
        #print pattern, s
        return bool(pat.search(s))

    def _test_ns_path(self, path, args):
        #print "**** test_path", repr(path), repr(args)
        pattern = iterparse_filter.to_regexp(path,
                            namespaces = {
            "xml": "http://www.w3.org/XML/1998/namespace",
            "das2": "http://biodas.org/documents/das2"},
                            # the empty namespace is not the same as no namespace!
                            default_namespace = "")
            
        pat = re.compile(pattern)
        s = "/" + ("/".join(args)) + "/"
        #print pattern, s
        return bool(pat.search(s))


    def test_syntax(self):
        for (xpath, tag_list, expect) in (
            ("A", ["A"], 1),
            ("A", ["AA"], 0),
            ("A", ["B", "A"], 1),
            ("/A", ["B", "A"], 0),
            ("/B", ["B", "A"], 0),
            ("//A", ["B", "A"], 1),
            ("A//B", ["A", "B"], 1),
            ("A//B", ["C", "A", "B"], 1),
            ("/A//B", ["C", "A", "B"], 0),
            ("/B/*", ["B", "A"], 1),
            # Test back-tracking; both greedy and non-greedy cases
            ("A//B//C//D", ["A", "B", "C", "B", "D"], 1),
            ("A//B/D", ["A", "B", "C", "B", "D"], 1),

            # Clark namespace tests
            ("{http://x.com}A", ["{http://x.com}A"], 1),
            ("{http://x.org}A", ["{http://x.com}A"], 0),
            ("{http://x.org}A", ["{http://x.com}B", "{http://x.org}A"], 1),
            ("*", ["{http://x.com}A"], 1),
            ("{http://x.com}*", ["{http://x.com}A"], 1),
            ("{http://x.com}*", ["{http://x.org}A"], 0),
            
            ):
            got = self._test_path(xpath, tag_list)
            self.assertEqual(got, expect)

        for (xpath, tag_list, expect) in (
            # various namespace checks
            ("xml:A", ["{http://www.w3.org/XML/1998/namespace}A"], 1),
            ("xml:A", ["{http://www.w3.org/XML/1998/namespace2}A"], 0),
            ("xml:A", ["{http://www.w3.org/XML/1998/namespace}AA"], 0),
            ("xml:A", ["{http://www.w3.org/XML/1998/namespace}B",
                        "{http://www.w3.org/XML/1998/namespace}A"], 1),
            ("xml:B", ["{http://www.w3.org/XML/1998/namespace}B",
                        "{http://www.w3.org/XML/1998/namespace}A"], 0),

            ("A", ["{}A"], 1),
            ("A", ["A"], 0),

            ("*", ["A"], 0),
            ("*", ["{}A"], 1),
            ("das2:*", ["{http://biodas.org/documents/das2}AAA"], 1),
            ("das2:*", ["{}AAA"], 0),
            ("xml:*/das2:*", ["{http://www.w3.org/XML/1998/namespace}ABC",
                                "{http://biodas.org/documents/das2}ABC"], 1),
            ("das2:*/xml:*", ["{http://www.w3.org/XML/1998/namespace}ABC",
                                "{http://biodas.org/documents/das2}ABC"], 0),
            

            ):
            got = self._test_ns_path(xpath, tag_list)
            self.assertEqual(got, expect)


    
    def test_filtering(self):
        f = io.BytesIO("""\
    <A><AA>
    <B xmlns="http://z/"><C/><spam:D xmlns:spam="http://spam/">eggs</spam:D></B>
    <B x='6'>foo<B y='7'>bar</B>baz</B>
    </AA></A>""".encode("utf-8"))
        special = object()
        class Capture(object):
            def __init__(self):
                self.history = []
            def __call__(self, event, ele, state):
                if state is not special:
                    raise AssertionError("Did not get expected state")
                self.history.append( (event, ele) )

        filter = iterparse_filter.IterParseFilter()
        capture_all = Capture()
        filter.on_start_document(capture_all)
        filter.on_start("*", capture_all)
        filter.on_end("*", capture_all)
        filter.on_end_document(capture_all)
        filter.on_start_ns(capture_all)
        filter.on_end_ns(capture_all)

        for x in filter.parse(f, state=special):
            raise AssertionError("should not yield %r" % (x,))

        expect_history = (
            ("start-document", None),
            ("start", "A"),
            ("start", "AA"),
            ("start-ns", ("", "http://z/")),
            ("start", "{http://z/}B"),
            ("start", "{http://z/}C"),
            ("end", "{http://z/}C"),
            ("start-ns", ("spam", "http://spam/")),
            ("start", "{http://spam/}D"),
            ("end", "{http://spam/}D"),
            ("end-ns", None),
            ("end", "{http://z/}B"),
            ("end-ns", None),
            ("start", "B"),
            ("start", "B"),
            ("end", "B"),
            ("end", "B"),
            ("end", "AA"),
            ("end","A"),
            ("end-document", None),
            )

        for (got, expect) in zip(capture_all.history, expect_history):
            event, ele = got
            tag = getattr(ele, "tag", ele)
            self.assertEqual((event, tag), expect)
        self.assertEqual(len(capture_all.history), len(expect_history))
                
        f.seek(0)
        filter = iterparse_filter.IterParseFilter()
        def must_match_B(event, ele, state):
            self.assertEqual(ele.tag, "B")

        def must_match_B_y7(event, ele, state):
            self.assertEqual(ele.tag, "B")
            self.assertEqual(ele.attrib["y"], "7")

        filter.on_start("B", must_match_B)
        filter.on_start("B/B", must_match_B_y7)
        
        f.seek


    @unittest.SkipTest
    def test_parse(self):
        import os
        filename = "/Users/dalke/Music/iTunes/iTunes Music Library.xml"
        if not os.path.exists(filename):
            print ("Cannot find %r: skipping test" % (filename,))
            return

        # Work through callbacks
        ef = IterParseFilter()
        def print_info(event, ele, state):
            d = {}
            children = iter(ele)
            for child in children:
                key = child.text
                value = children.next().text
                d[key] = value
            print ("%r is by %r" % (d["Name"], d.get("Artist", "<unknown>")))
            ele.clear()
                
        ef.on_end("/plist/dict/dict/dict", print_info)
        ef.handler_parse(open(filename))

        # Work through iterators
        ef = IterParseFilter()
        ef.iter_end("/plist/dict/dict/dict")
        for (event, ele) in ef.iterparse(open(filename)):
            d = {}
            children = iter(ele)
            for child in children:
                key = child.text
                value = children.next().text
                d[key] = value
            print ("%r is a %r song" % (d["Name"], d.get("Genre", "<unknown>")))
            ele.clear()

if __name__ == "__main__":
    unittest.main()