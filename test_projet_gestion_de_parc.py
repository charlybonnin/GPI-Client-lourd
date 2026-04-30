import unittest
import tempfile
from datetime import datetime, timedelta
from projet_gestion_de_parc import Database, validate_date, Application

class TestDatabase(unittest.TestCase):
    """Tests pour la classe Database."""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db = Database(self.temp_db.name)

    def tearDown(self):
        if self.db.conn:
            self.db.conn.close()
        import os
        os.unlink(self.temp_db.name)

    def test_connexion(self):
        # Test si la DB se connecte
        self.assertTrue(self.db.is_connected())

    def test_table_creee(self):
        # Vérifier que la table existe
        self.db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='equipement'")
        result = self.db.cursor.fetchone()
        self.assertIsNotNone(result)

    def test_insert_et_fetch(self):
        # Ajouter un équipement et le récupérer
        future_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        self.db.execute("INSERT INTO equipement (nom, numSerie, dateFinGarantie, etat, id_salle, id_type_equipement) VALUES (?, ?, ?, ?, ?, ?)", ("PC", "123", future_date, "Bon état", 1, "Portable"))
        data = self.db.fetch("equipement")
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["nom"], "PC")

class TestValidateDate(unittest.TestCase):
    """Tests pour la fonction validate_date."""

    def test_date_future(self):
        # Test date dans le futur
        future_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        is_valid, msg = validate_date(future_date)
        self.assertTrue(is_valid)

    def test_date_passee(self):
        # Test date passée
        past_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        is_valid, msg = validate_date(past_date)
        self.assertFalse(is_valid)

    def test_format_mauvais(self):
        # Test format invalide
        is_valid, msg = validate_date("25/12/2023")
        self.assertFalse(is_valid)

class TestApplication(unittest.TestCase):
    """Tests pour la classe Application."""

    def setUp(self):
        import tkinter as tk
        self.root = tk.Tk()
        self.app = Application()
        self.app.master = self.root  # Pour éviter les problèmes

    def tearDown(self):
        self.root.destroy()

    def test_load_equipements(self):
        # Test que load_equipements ne plante pas
        self.app.load_equipements()
        # Test avec filtre
        self.app.load_equipements("id_salle = ?", [1])

if __name__ == '__main__':
    unittest.main()