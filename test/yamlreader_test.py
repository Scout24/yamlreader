import unittest
import logging
import sys
from yamlreader import *
from yamlreader import data_merge


class Test(unittest.TestCase):
    
    data1_test1 = {'data1': 'test5', 'data2': [{'test3': 'data4', 'test5': 'data5'}]}
    
    data1_merged = {
                    'data1': 'test1',
                    'data2': [{
                               'test3': 'data4',
                               'test5': 'data5'
                               },
                            {
                                'test6': 'data6'
                            }]
}
    
    data1_merged_plus_default = {
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
    loghandler.setFormatter(logging.Formatter('yamlreader_test[%(filename)s:%(lineno)d]: %(levelname)s: %(message)s'))
    logger.addHandler(loghandler)
    logger.setLevel(logging.DEBUG)

    def test_should_correctly_merge_single_yaml_file(self):
        self.assertEqual(yaml_load("testdata/data1/test1.yaml"), self.data1_test1)
        
    def test_should_correctly_merge_list_of_yaml_files(self):
        self.assertEqual(yaml_load(["testdata/data1/test1.yaml", "testdata/data1/test2.yaml"]), self.data1_merged)
        
    def test_should_correctly_merge_tuple_of_yaml_files(self):
        self.assertEqual(yaml_load(("testdata/data1/test1.yaml", "testdata/data1/test2.yaml")), self.data1_merged)
        
    def test_should_correctly_merge_glob_of_yaml_files(self):
        self.assertEqual(yaml_load("testdata/data1/test?.yaml"), self.data1_merged)
        
    def test_should_correctly_merge_dir_of_yaml_files(self):
        self.assertEqual(yaml_load("testdata/data1"), self.data1_merged)

    def test_should_correctly_merge_dir_of_yaml_files_given_as_list(self):
        self.assertEqual(yaml_load(["testdata/data1"]), self.data1_merged)

    def test_should_correctly_merge_dir_of_yaml_files_with_default(self):
        self.assertEqual(yaml_load("testdata/data1", defaultdata={"data3":"foo"}), self.data1_merged_plus_default)

    def test_should_return_default_data_if_invalid_file_given(self):
        self.assertEqual(yaml_load("testdata/invalid", defaultdata={"foo":"bar"}), {"foo":"bar"})

    def test_should_fail_on_invalid_yaml_file(self):
        self.assertRaises(YamlReaderError, yaml_load, "setup.cfg")

    def test_should_fail_on_invalid_glob(self):
        self.assertRaises(YamlReaderError, yaml_load, "testdata/gaga*")

    def test_should_return_default_data_if_empty_file_given(self):
        self.assertEqual(yaml_load("/dev/null", defaultdata={"foo":"bar"}), {"foo":"bar"})

    def test_should_fail_on_invalid_yaml_dir(self):
        self.assertRaises(YamlReaderError, yaml_load, "testdata")
    
    def test_should_return_default_data_if_invalid_dir_given(self):
        self.assertEqual(yaml_load("testdata", defaultdata={"foo":"bar"}), {"foo":"bar"})

    def test_merge_complex_list_to_list(self):
        self.assertEqual(data_merge([1, 2], [{1:2}, 1]), [1, 2, {1: 2}, 1])
        
    def test_merge_dict_to_list(self):
        self.assertEqual(data_merge([1, 2], {1:2}), [1, 2, {1: 2}])

    def test_merge_string_to_list(self):
        self.assertEqual(data_merge([1, 2], "hello"), [1, 2, "hello"])
        
    def test_merge_tuple_to_list(self):
        self.assertEqual(data_merge([1, 2], ({1:2}, 3)), [1, 2, ({1: 2}, 3)])
        
    def test_merge_dict_to_dict(self):
        self.assertEqual(data_merge({1:2,3:[1,2,3]},{3:6}),{1:2,3:[1,2,3,6]})
    
    def test_merge_deep_dict_to_deep_dict(self):
        self.assertEqual(data_merge({1:2,3:{1:2}},{3:{2:5}}),{1: 2, 3: {1: 2, 2: 5}})
    
    def test_failt_to_merge_string_to_tuple(self):
        self.assertRaises(YamlReaderError,data_merge,(1,2,3),"hello")
        
    def test_fail_to_merge_string_to_dict(self):
        self.assertRaises(YamlReaderError,data_merge,{1:2},"hello")

    def test_fail_to_merge_list_to_dict(self):
        self.assertRaises(YamlReaderError,data_merge,{1:2},[3,2])

if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.test_should_return_default_data_if_invalid_file_given']
    unittest.main()
