import unittest
import os

class SanityTestCase(unittest.TestCase):
    def test_sanity(self):
        self.assertTrue(True, "Basic sanity test passed")
    
    def test_environment(self):
        import sys
        print("\nPython version:", sys.version)
        print("Current directory:", os.getcwd())
        print("Files in directory:", os.listdir('.'))
        self.assertTrue(True)