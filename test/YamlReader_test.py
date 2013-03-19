import unittest
import logging
import sys
from yaml_server.YamlReader import YamlReader
from yaml_server.YamlServerException import YamlServerException


class Test(unittest.TestCase):
    
    data1_data = {'data1': 'test5', 'data2': [{'test3': 'data4', 'test5': 'data5'}]}
    
    data2_data = {
                   'data1': 'test1',
                   'data2': [
                            {
                                'test3': 'data4',
                                'test5': 'data5'
                            },
                            {
                                'test6': 'data6'
                            }
                            ],
                    'data3': 'foo'
                  }

    logger = logging.getLogger()
    loghandler = logging.StreamHandler()
    loghandler.setFormatter(logging.Formatter('yaml_server[%(filename)s:%(lineno)d]: %(levelname)s: %(message)s'))
    logger.addHandler(loghandler)
    logger.setLevel(logging.DEBUG)
    
    def test_should_correctly_merge_single_yaml_file(self):
        self.assertEqual(YamlReader("testdata/data1/test1.yaml",displayname="test_should_correctly_merge_single_yaml_file").get(),self.data1_data)
        
    def test_should_correctly_merge_yaml_files_from_dir(self):
        self.assertEqual(YamlReader("testdata/data1", defaultdata={"data3":"foo"},displayname="test_should_correctly_merge_yaml_files_from_dir").get(), self.data2_data)

    def test_should_fail_on_invalid_yaml_dir(self):
        self.assertRaises(YamlServerException, YamlReader, "/dev/null",displayname="test_should_fail_on_invalid_yaml_dir")
    
    def test_should_return_default_data_if_invalid_file_given(self):
        self.assertEqual(YamlReader("/dev/null",defaultdata={"foo":"bar"},displayname="test_should_return_default_data_if_invalid_file_given").get(), {"foo":"bar"})

    def test_should_fail_on_invalid_yaml_file(self):
        self.assertRaises(YamlServerException, YamlReader, "setup.cfg",displayname="test_should_fail_on_invalid_yaml_file")

    def test_should_return_default_data_if_invalid_dir_given(self):
        self.assertEqual(YamlReader("/",defaultdata={"foo":"bar"},displayname="test_should_return_default_data_if_invalid_dir_given").get(), {"foo":"bar"})
        
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.test_should_return_default_data_if_invalid_file_given']
    unittest.main()
