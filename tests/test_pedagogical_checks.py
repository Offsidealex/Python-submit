"""Tests indépendants des règles AST réellement utilisées par Python Submit."""
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/"tests"))
from pedagogical_checks import REQUIREMENTS, validate_code
from virtual_student import SOLUTIONS, catalogue, execute
from audit_pedagogique import OTHER_METHODS


class StructurePedagogique(unittest.TestCase):
    def test_solutions_de_reference(self):
        for exercise in catalogue():
            source=SOLUTIONS[exercise["id"]]
            with self.subTest(exercise=exercise["id"]):
                self.assertTrue(validate_code(exercise["id"],source)["ok"],
                                validate_code(exercise["id"],source))

    def test_variantes_correctes_tp1_a_tp3(self):
        for exercise_id,source in OTHER_METHODS.items():
            with self.subTest(exercise=exercise_id):
                self.assertTrue(validate_code(exercise_id,source)["ok"],
                                validate_code(exercise_id,source))

    def test_commentaires_ne_simulent_pas_une_solution(self):
        for exercise_id in REQUIREMENTS:
            code="print('RÉPONSE') # while random.randint == for if type() def"
            with self.subTest(exercise=exercise_id):
                self.assertFalse(validate_code(exercise_id,code)["ok"],
                                 exercise_id+" a accepté un programme sans méthode")

    def test_dice_variable_et_import_direct(self):
        for sample in (
            """import random
n=0
while True:
 a=random.randint(1,6)
 b=random.randint(1,6)
 n+=1
 if a==b: break
print(n)
""",
            """from random import randint
a,b=0,1
n=0
while a!=b:
 a=randint(1,6)
 b=randint(1,6)
 n+=1
print(n)
""",
        ):
            with self.subTest(program=sample[:25]):
                self.assertTrue(validate_code("tp3q4",sample)["ok"])
                self.assertEqual(execute(sample,[],[1,2,3,4,5,5]),"3")
                self.assertEqual(execute(sample,[],[4,4]),"1")

    def test_dice_false_claims_rejected(self):
        frauds=(
            "print(3) # while random.randint(1,6) ==",
            """import random
for i in range(3):
 a=random.randint(1,6)
 b=random.randint(1,6)
print(3)""",
            """import random
while False:
 a=random.randint(1,6)
 b=random.randint(1,6)
print(1)""",
        )
        for code in frauds[:2]:
            with self.subTest(program=code[:30]):
                self.assertFalse(validate_code("tp3q4",code)["ok"])
        # Ce troisième cas passe volontairement l'analyse de forme :
        # les tirages déterministes supplémentaires doivent refuser sa sortie.
        dead_code=frauds[2]
        self.assertFalse(
            all(execute(dead_code,[],rolls)==str(expected)
                for rolls,expected in [([1,2,3,4,5,5],3),([4,4],1)])
        )

    def test_rejets_ciblés(self):
        cases={
            "tp1q1":"print('Tension U = 9.4 V')",
            "tp1q2":"print(\"<class 'int'>\\n<class 'float'>\\n<class 'str'>\")",
            "tp2q3":"print('Système déclenché') # and",
            "tp2q4":"for A in range(2): print(A) # seconde boucle",
            "tp3q1":"print('Année 1 : 21200 €')",
            "tp3q3":"print(20100);print(20100)",
            "tp3q4":"print(1)",
            "tp4q1":"print(9.4)",
            "tp8q1":"print('Fichier créé')",
            "tp10q2":"print('OK\\nALERTE')",
        }
        for exercise_id,code in cases.items():
            with self.subTest(exercise=exercise_id):
                self.assertFalse(validate_code(exercise_id,code)["ok"])

    def test_python_invalide(self):
        self.assertFalse(validate_code("tp3q4","while :\n pass")["ok"])

    def test_garde_une_méthode_de_lecture_idiomatique(self):
        code=SOLUTIONS["tp8q3"]
        self.assertTrue(validate_code("tp8q3",code)["ok"])

    def test_at_least_30_exercices_couverts(self):
        self.assertGreaterEqual(len(REQUIREMENTS),30)


if __name__=="__main__":
    unittest.main(verbosity=2)
