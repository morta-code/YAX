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

        self.e_plant_columbine = etree.fromstring(
            """
<PLANT>
    <COMMON>Columbine</COMMON>
    <BOTANICAL>Aquilegia canadensis</BOTANICAL>
    <ZONE>3</ZONE>
    <LIGHT>Mostly Shady</LIGHT>
    <PRICE>$9.37</PRICE>
    <AVAILABILITY>030699</AVAILABILITY>
</PLANT>
            """
        )

        self.e_lineup = etree.fromstring('<lineup event_participantsFK="2278405" participantFK=' +
                                         '"100612" lineup_typeFK="5" shirt_number="0" pos="0" ' +
                                         'enet_pos="0" del="no" n="0" ut="2011-03-14 23:46:57" ' +
                                         'id="2743035"><participant name="Mike Brown" gender=' +
                                         '"undefined" type="athlete" countryFK="652" enetID=' +
                                         '"3082" enetSportID="ih" del="no" n="0" ut="2010-10-05 ' +
                                         '15:26:58" id="100612"></participant></lineup>')

        self.e_lineup2 = etree.fromstring(
            """
<lineup event_participantsFK="2278405" participantFK="99417" lineup_typeFK="5" shirt_number="0" pos="0" enet_pos="0" del="no" n="0" ut="2011-03-14 23:46:57" id="2743037">
    <participant name="Brett Lebda" gender="undefined" type="athlete" countryFK="16" enetID="2368" enetSportID="ih" del="no" n="1" ut="2010-10-05 12:57:57" id="99417"></participant>
</lineup>
            """
        )

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

        c = Condition(["PLANT", "plant", "Plant", re.compile("plant", re.I), lambda s: re.match(
            "cat", s, re.I) is not None])
        self.assertTrue(c.check(self.e_plant_hepatica))
        self.assertTrue(c.check(etree.fromstring("<PLANT/>")))
        self.assertTrue(c.check(etree.fromstring("<Plant/>")))
        self.assertTrue(c.check(etree.fromstring("<PlAnT/>")))
        self.assertTrue(c.check(etree.fromstring("<CATALOG/>")))
        self.assertFalse(c.check(etree.fromstring("<plant2/>")))
        self.assertFalse(c.check(self.e_plant_columbine[1]))

    def test_only_attrib_condition(self):
        c = Condition(attrib={"participantFK": "100612"})
        self.assertTrue(c.check(self.e_lineup))
        self.assertFalse(c.check(self.e_plant_hepatica))
        self.assertFalse(c.check(self.e_lineup2))

        c = Condition(attrib={"participantFK": [lambda d: int(d) > 100100, "100000"]})
        self.assertTrue(c.check(self.e_lineup))
        self.assertFalse(c.check(self.e_plant_hepatica))

        c = Condition(attrib={"participantFK": True})
        self.assertTrue(c.check(self.e_lineup))
        self.assertTrue(c.check(self.e_lineup2))
        self.assertFalse(c.check(self.e_plant_hepatica))

        c = Condition(attrib={"participantFK": re.compile("\d+")})
        self.assertTrue(c.check(self.e_lineup))
        self.assertTrue(c.check(self.e_lineup2))
        self.assertFalse(c.check(self.e_plant_hepatica))

        c = Condition(attrib={"participantFK": lambda d: int(d) > 100000})
        self.assertTrue(c.check(self.e_lineup))
        self.assertFalse(c.check(self.e_lineup2))

        c = Condition(attrib={"name": re.compile("Brett.*"), "countryFK": lambda s: int(s) > 1,
                              "del": True})
        self.assertFalse(c.check(self.e_lineup2))
        self.assertTrue(c.check(self.e_lineup2[0]))
        self.assertFalse(c.check(self.e_lineup[0]))

    def test_only_text_condition(self):
        c = Condition(text="Hepatica")
        self.assertFalse(c.check(self.e_plant_hepatica))
        self.assertFalse(c.check(self.e_plant_hepatica[1]))
        self.assertTrue(c.check(self.e_plant_hepatica[0]))

        c = Condition(text=re.compile("Hepatica"))
        self.assertFalse(c.check(self.e_plant_hepatica))
        self.assertFalse(c.check(self.e_plant_hepatica[1]))
        self.assertTrue(c.check(self.e_plant_hepatica[0]))

        c = Condition(text=re.compile("Hepatica.*"))
        self.assertFalse(c.check(self.e_plant_hepatica))
        self.assertTrue(c.check(self.e_plant_hepatica[1]))
        self.assertTrue(c.check(self.e_plant_hepatica[0]))

        c = Condition(text=True)
        self.assertFalse(c.check(self.e_plant_columbine))
        self.assertTrue(c.check(self.e_plant_columbine[0]))

        c = Condition(text=[re.compile("Hepatica.*"), "Columbine", lambda x: float(x[1:]) < 5])
        self.assertFalse(c.check(self.e_plant_columbine))
        self.assertTrue(c.check(self.e_plant_columbine[0]))
        self.assertTrue(c.check(self.e_plant_hepatica[1]))
        self.assertTrue(c.check(self.e_plant_hepatica[4]))
        self.assertFalse(c.check(self.e_plant_columbine[4]))

    def test_complex_conditions(self):
        c = Condition("PLANT", children={"tag": "PRICE", "text": lambda x: float(x[1:]) < 5.1})
        self.assertTrue(c.check(self.e_plant_hepatica))
        self.assertFalse(c.check(self.e_plant_columbine))

        c = Condition("PLANT", children=("PRICE", None, "$4.45"))
        self.assertTrue(c.check(self.e_plant_hepatica))

        c = Condition("PLANT", children=[{"tag": "PRICE", "text": "$4.45"}, "COMMON"])
        self.assertTrue(c.check(self.e_plant_hepatica))
        self.assertFalse(c.check(etree.fromstring("""
        <PLANT>
            <PRICE>$4.45</PRICE>
            <NAME>name</NAME>
        </PLANT>
        """)))

        c = Condition(tag=["PLANT", "plant"],
                      parent=("CATALOG", {'name': "first"}),
                      children=[("PRICE", None, "$5"), ("NAME", None, re.compile("[A-Z]\w*"))],
                      keep_children=Condition(text=True))
        self.assertFalse(c.check(self.e_plant_hepatica))
        self.assertTrue(c.check(etree.fromstring("""
        <CATALOG name="first">
            <plant>
                <PRICE>$5</PRICE>
                <NAME>Nagybetu</NAME>
            </plant>
        </CATALOG>
        """)[0]))
        self.assertFalse(c.check(etree.fromstring("""
        <CATALOG>
            <plant>
                <PRICE>$5</PRICE>
                <NAME>Nagybetu</NAME>
            </plant>
        </CATALOG>
        """)[0]))
        self.assertFalse(c.check(etree.fromstring("""
        <CATALOG name="first">
            <PLANT>
                <PRICE>$5</PRICE>
                <NAME>kisbetu</NAME>
            </PLANT>
        </CATALOG>
        """)[0]))

    def test_wrong_conditions(self):
        with self.assertRaises(AttributeError):
            # Invalid tagname
            Condition(5)
        with self.assertRaises(AttributeError):
            # Tuple instead of list. Tuple means initialize list
            Condition(("plant", "PLANT"))
        with self.assertRaises(AttributeError):
            # Search by sibling.
            Condition(parent=Condition(children="CHILD"))
        with self.assertRaises(AttributeError):
            # Cannot search attribute non-existance
            Condition(attrib={"participantFK": False})

if __name__ == '__main__':
    unittest.main()
