__author__ = 'Tamás'

import unittest
from lxml import etree
from yax.YAXReader import Condition
import re


class MyTestCase(unittest.TestCase):

    def setUp(self):
        self.e_plant_hepatica = etree.fromstring("<PLANT><COMMON>Hepatica</COMMON><BOTANICAL>" +
                                                 "Hepatica americana</BOTANICAL><ZONE>4</ZONE>" +
                                                 "<LIGHT>Mostly Shady</LIGHT><PRICE>$4.45</PRICE>" +
                                                 "<AVAILABILITY>012699""</AVAILABILITY></PLANT>")

        self.e_plant_columbine = etree.fromstring("<PLANT><COMMON>Columbine</COMMON><BOTANICAL>" +
                                                  "Aquilegia canadensis</BOTANICAL><ZONE>3</ZONE>" +
                                                  "<LIGHT>Mostly " +
                                                  "Shady</LIGHT><PRICE>$9.37</PRICE>" +
                                                  "<AVAILABILITY>030699</AVAILABILITY></PLANT>")

    def tearDown(self):
        pass

    def test_only_tag_condition(self):
        c = Condition("PLANT")
        self.assertTrue(c.check(self.e_plant_hepatica), "A c Condition nem teljesül")
        self.assertTrue(c.check(etree.fromstring("<PLANT/>")), "A c Condition nem teljesül")
        self.assertFalse(c.check(etree.fromstring("<plant/>")), "A c Condition nem hamis")
        self.assertFalse(c.check(self.e_plant_columbine[1]), "A c Condition nem hamis")

        d = Condition(re.compile("plant", re.I))
        self.assertTrue(d.check(self.e_plant_hepatica), "A d Condition nem teljesül")
        self.assertTrue(d.check(etree.fromstring("<plant/>")), "A d Condition nem teljesül")
        self.assertTrue(d.check(etree.fromstring("<PlAnT/>")), "A d Condition nem teljesül")
        self.assertFalse(d.check(self.e_plant_columbine[1]), "A d Condition nem hamis")
        self.assertFalse(d.check(etree.fromstring("<plant2/>")), "A d Condition nem hamis")

        e = Condition(lambda s: s == "PLANT")
        self.assertTrue(e.check(self.e_plant_hepatica), "Az e Condition nem teljesül")
        self.assertTrue(e.check(etree.fromstring("<PLANT/>")), "Az e Condition nem teljesül")
        self.assertFalse(e.check(self.e_plant_columbine[1]), "Az e Condition nem hamis")
        self.assertFalse(e.check(etree.fromstring("<plant2/>")), "Az e Condition nem hamis")

        f = Condition(["PLANT", "plant", "Plant"])
        self.assertTrue(f.check(self.e_plant_hepatica), "Az f Condition nem teljesül")
        self.assertTrue(f.check(etree.fromstring("<PLANT/>")), "Az f Condition nem teljesül")
        self.assertTrue(f.check(etree.fromstring("<Plant/>")), "Az f Condition nem teljesül")
        self.assertFalse(f.check(self.e_plant_columbine[1]), "Az f Condition nem hamis")
        self.assertFalse(f.check(etree.fromstring("<plant2/>")), "Az f Condition nem hamis")

    def test_only_attrib(self):
        pass

if __name__ == '__main__':
    unittest.main()
