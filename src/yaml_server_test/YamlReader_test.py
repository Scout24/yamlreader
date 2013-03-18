import unittest
import logging
from yaml_server.YamlReader import YamlReader
from yaml_server.YamlServerException import YamlServerException


class Test(unittest.TestCase):
    
    data1_data = {
                   'data1': 'test1',
                   'data2': [
                            {
                                'test3': 'data4',
                                'test5': 'data5'
                            }, 
                            {
                                'test6': 'data6'
                            }
                            ]
                  }

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.logger = logging.getLogger()
        self.loghandler = logging.StreamHandler()
        self.loghandler.setFormatter(logging.Formatter('yaml_server[%(module)s %(funcName)s]: %(levelname)s: %(message)s'))
        self.logger.addHandler(self.loghandler)
        self.logger.setLevel(logging.DEBUG)
        
        
    def test_should_correctly_merge_yaml_files(self):
        self.assertEqual(YamlReader("testdata/data1").get(), self.data1_data)

    def test_should_fail_on_invalid_yaml_dir(self):
        self.assertRaises(YamlServerException, YamlReader,"/dev/null")


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
