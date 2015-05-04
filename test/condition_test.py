__author__ = 'Tamás'

import unittest
from lxml import etree
from yax.YAXReader import Condition
import re


class ConditionTest(unittest.TestCase):

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

        self.e_lineup = etree.fromstring('<lineup event_participantsFK="2278405" participantFK=' +
                                         '"100612" lineup_typeFK="5" shirt_number="0" pos="0" ' +
                                         'enet_pos="0" del="no" n="0" ut="2011-03-14 23:46:57" ' +
                                         'id="2743035"><participant name="Mike Brown" gender=' +
                                         '"undefined" type="athlete" countryFK="652" enetID=' +
                                         '"3082" enetSportID="ih" del="no" n="0" ut="2010-10-05 ' +
                                         '15:26:58" id="100612"></participant></lineup>')

    def tearDown(self):
        pass

    def test_only_tag_condition(self):
        c = Condition("PLANT")
        self.assertTrue(c.check(self.e_plant_hepatica))
        self.assertTrue(c.check(etree.fromstring("<PLANT/>")))
        self.assertFalse(c.check(etree.fromstring("<plant/>")))
        self.assertFalse(c.check(self.e_plant_columbine[1]))

        c = Condition(re.compile("plant", re.I))
        self.assertTrue(c.check(self.e_plant_hepatica))
        self.assertTrue(c.check(etree.fromstring("<plant/>")))
        self.assertTrue(c.check(etree.fromstring("<PlAnT/>")))
        self.assertFalse(c.check(self.e_plant_columbine[1]))
        self.assertFalse(c.check(etree.fromstring("<plant2/>")))

        c = Condition(lambda s: s == "PLANT")
        self.assertTrue(c.check(self.e_plant_hepatica))
        self.assertTrue(c.check(etree.fromstring("<PLANT/>")))
        self.assertFalse(c.check(self.e_plant_columbine[1]))
        self.assertFalse(c.check(etree.fromstring("<plant2/>")))

        c = Condition(["PLANT", "plant", "Plant", re.compile("plant", re.I)])
        self.assertTrue(c.check(self.e_plant_hepatica))
        self.assertTrue(c.check(etree.fromstring("<PLANT/>")))
        self.assertTrue(c.check(etree.fromstring("<Plant/>")))
        self.assertTrue(c.check(etree.fromstring("<PlAnT/>")))
        self.assertFalse(c.check(etree.fromstring("<plant2/>")))
        self.assertFalse(c.check(self.e_plant_columbine[1]))

    def test_only_attrib(self):
        c = Condition(attrib={"participantFK": "100612"})
        self.assertTrue(c.check(self.e_lineup))
        self.assertFalse(c.check(self.e_plant_hepatica))

        c = Condition(attrib={"participantFK": ["100612", "100000"]})
        self.assertTrue(c.check(self.e_lineup))

        c = Condition(attrib={"participantFK": True})
        self.assertTrue(c.check(self.e_lineup))
        self.assertFalse(c.check(self.e_plant_hepatica))

        c = Condition(attrib={"participantFK": re.compile("\d+")})
        self.assertTrue(c.check(self.e_lineup))

        c = Condition(attrib={"participantFK": lambda d: int(d) > 10000})
        self.assertTrue(c.check(self.e_lineup))

    def test_wrong_conditions(self):
        with self.assertRaises(AttributeError):
            Condition(5)
        with self.assertRaises(AttributeError):
            Condition(("plant", "PLANT"))
        with self.assertRaises(AttributeError):
            Condition(parent=Condition(children="CHILD"))

if __name__ == '__main__':
    unittest.main()
